#!/usr/bin/env python3
"""
RAG PDF Checker - Software Design Book Contradiction Detector
This tool analyzes PDF chapters for logical contradictions using RAG and vector similarity.
"""

import os
import re
import json
import logging
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib

import pdfplumber
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from tqdm import tqdm
from colorama import init, Fore, Style
from dotenv import load_dotenv

# Initialize colorama for colored output
init()

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Represents a chapter from the PDF"""
    pdf_name: str
    chapter_number: str
    title: str
    content: str
    page_start: int
    page_end: int
    
    def get_id(self) -> str:
        """Generate unique ID for the chapter"""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()[:8]
        return f"{self.pdf_name}_{self.chapter_number}_{content_hash}"


@dataclass
class Contradiction:
    """Represents a detected contradiction between documents/segments"""
    doc1_id: str
    doc2_id: str
    doc1_excerpt: str
    doc2_excerpt: str
    contradiction_type: str
    explanation: str
    confidence_score: float


class PDFChapterExtractor:
    """Extracts chapters from PDF files"""
    
    # Common chapter patterns in various languages
    CHAPTER_PATTERNS = [
        r'(?:Chapter|CHAPTER)\s+(\d+|[IVX]+)',  # English with numbers or Roman
        r'(\d+)\s*장',  # Korean
        r'제\s*(\d+)\s*장',  # Korean alternative
        r'Chapter\s*(\d+)\s*[:\-.]',  # Chapter with punctuation
        r'^\s*(\d+)\.\s+',  # Simple numbering (1. Title)
        r'PART\s+(\d+|[IVX]+)',  # Part instead of chapter
    ]
    
    def extract_chapters(self, pdf_path: str) -> List[Chapter]:
        """Extract chapters from a PDF file"""
        chapters = []
        pdf_name = Path(pdf_path).stem
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Extract all text with page numbers
                pages_text = []
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    pages_text.append((i + 1, text))
                
                # Find chapter boundaries
                chapter_starts = self._find_chapter_starts(pages_text)
                
                # Extract chapters based on boundaries
                for i, (page_num, chapter_match) in enumerate(chapter_starts):
                    # Determine end page
                    if i + 1 < len(chapter_starts):
                        end_page = chapter_starts[i + 1][0] - 1
                    else:
                        end_page = len(pdf.pages)  # Total number of pages
                    
                    # Collect chapter content
                    chapter_content = []
                    for page_idx in range(page_num - 1, end_page):
                        if page_idx < len(pages_text):
                            chapter_content.append(pages_text[page_idx][1])
                    
                    content = '\n'.join(chapter_content)
                    
                    # Extract chapter title (first few lines after chapter marker)
                    lines = content.split('\n')
                    title = ' '.join(lines[:3]).strip()[:100]  # First 3 lines, max 100 chars
                    
                    chapter = Chapter(
                        pdf_name=pdf_name,
                        chapter_number=chapter_match,
                        title=title,
                        content=content,
                        page_start=page_num,
                        page_end=end_page
                    )
                    chapters.append(chapter)
                    
                logger.info(f"Extracted {len(chapters)} chapters from {pdf_name}")
                
        except Exception as e:
            logger.error(f"Error extracting chapters from {pdf_path}: {e}")
            
        return chapters
    
    def _find_chapter_starts(self, pages_text: List[Tuple[int, str]]) -> List[Tuple[int, str]]:
        """Find chapter start positions in the PDF"""
        chapter_starts = []
        
        for page_num, text in pages_text:
            # Check each line for chapter patterns
            lines = text.split('\n')[:10]  # Check first 10 lines of each page
            
            for line in lines:
                for pattern in self.CHAPTER_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        # Extract chapter number from the first capturing group
                        if match.groups():
                            chapter_num = match.group(1)
                        else:
                            chapter_num = str(len(chapter_starts) + 1)
                        chapter_starts.append((page_num, chapter_num))
                        break
                else:
                    continue
                break
        
        return chapter_starts


class EmbeddingManager:
    """Manages text embeddings using OpenAI or HuggingFace"""
    
    def __init__(self, model_type: str = "openai"):
        self.model_type = model_type
        
        if model_type == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.embedding_model = "text-embedding-3-small"
            self.embedding_dim = 1536  # text-embedding-3-small dimension
        else:
            # HuggingFace implementation can be added here
            raise NotImplementedError("HuggingFace embeddings not yet implemented")
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text"""
        try:
            # Truncate text if too long (OpenAI has token limits)
            if len(text) > 8000:
                text = text[:8000]
                
            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return [0.0] * self.embedding_dim


class VectorStore:
    """Manages Qdrant vector database operations"""
    
    def __init__(self, collection_name: str = "book_chapters"):
        self.collection_name = collection_name
        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6345))
        )
        self.embedding_dim = 1536  # OpenAI embedding dimension
        
        self._init_collection()
    
    def _init_collection(self):
        """Initialize or recreate the collection"""
        try:
            # Delete existing collection if exists
            self.client.delete_collection(self.collection_name)
        except:
            pass
            
        # Create new collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )
        logger.info(f"Initialized collection: {self.collection_name}")
    
    def add_chapter(self, chapter: Chapter, embedding: List[float]):
        """Add a chapter with its embedding to the vector store"""
        # Generate numeric ID from hash
        chapter_id = abs(hash(chapter.get_id())) % (10 ** 12)
        
        point = PointStruct(
            id=chapter_id,
            vector=embedding,
            payload={
                "chapter_id": chapter.get_id(),
                "pdf_name": chapter.pdf_name,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "content": chapter.content[:1000],  # Store first 1000 chars
                "page_start": chapter.page_start,
                "page_end": chapter.page_end
            }
        )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
    
    def search_similar(self, query_vector: List[float], limit: int = 5) -> List[Dict]:
        """Search for similar chapters"""
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]


class ContradictionDetector:
    """Detects contradictions between chapters using LLM"""
    
    def __init__(self, model_type="claude"):
        """Initialize detector with specified model type
        
        Args:
            model_type: "claude" (default) or "openai"
        """
        if model_type == "openai":
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = "gpt-4o"
            self.model_type = "openai"
        elif model_type == "claude":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            self.model = "claude-sonnet-4-20250514"
            self.model_type = "claude"
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    def detect_contradiction(self, chapter1: Chapter, chapter2: Chapter) -> Optional[Contradiction]:
        """Detect if two chapters contain contradictions"""
        
        # Create a focused prompt for contradiction detection
        # Parse chapter info to avoid confusion
        ch1_parts = chapter1.chapter_number.split('_')
        ch2_parts = chapter2.chapter_number.split('_')
        
        # Extract main document name and section
        ch1_main = ch1_parts[0] if ch1_parts else "Document"
        ch1_section = ch1_parts[-1] if len(ch1_parts) > 1 and ch1_parts[-1].isdigit() else ""
        ch2_main = ch2_parts[0] if ch2_parts else "Document"  
        ch2_section = ch2_parts[-1] if len(ch2_parts) > 1 and ch2_parts[-1].isdigit() else ""
        
        prompt = f"""You are analyzing two text segments from software design documentation for logical contradictions.

First Document: {ch1_main}{f" Section {ch1_section}" if ch1_section else ""}
Title: {chapter1.title}
Content excerpt: {chapter1.content[:2000]}

Second Document: {ch2_main}{f" Section {ch2_section}" if ch2_section else ""}
Title: {chapter2.title}
Content excerpt: {chapter2.content[:2000]}

Analyze these text segments and identify any logical contradictions. A contradiction occurs when:
1. One segment states something as true while another states it as false
2. Incompatible definitions or explanations of the same concept
3. Conflicting recommendations or best practices
4. Mutually exclusive claims about the same topic

If you find a contradiction:
1. Quote the specific contradicting statements from each segment
2. Explain why they contradict each other
3. Rate your confidence (0.0-1.0) that this is a real contradiction

Please respond in JSON format with the following structure:
{{
    "has_contradiction": true/false,
    "doc1_excerpt": "exact quote from first document",
    "doc2_excerpt": "exact quote from second document",
    "contradiction_type": "definition|recommendation|fact|principle",
    "explanation": "모순에 대한 상세한 설명을 한글로 작성하세요.",
    "confidence_score": 0.0-1.0
}}

IMPORTANT: When referring to the sources in your explanation, use:
- "첫 번째 문서" or "첫 번째 텍스트" (NOT "첫 번째 챕터" or "1장")
- "두 번째 문서" or "두 번째 텍스트" (NOT "두 번째 챕터" or "2장")
- If referring to sections, say "섹션 5" or "섹션 6", NOT "5장" or "6장"

If no contradiction is found, set has_contradiction to false and return the JSON object with empty strings for the other fields.
"""
        
        try:
            if self.model_type == "openai":
                # Add explicit JSON format request to the prompt
                system_prompt = "You are an expert at analyzing technical documentation for logical consistency. You MUST provide all explanations in Korean (한글)."
                prompt_with_json = prompt + "\n\nPlease respond in JSON format. IMPORTANT: The 'explanation' field MUST be written in Korean (한글)."
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_with_json}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(response.choices[0].message.content)
                
            elif self.model_type == "claude":
                # Claude requires different format
                system_prompt = "You are an expert at analyzing technical documentation for logical consistency. You MUST provide all explanations in Korean (한글). Always respond with valid JSON format only."
                
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": prompt + "\n\nRemember to respond with valid JSON format only."}
                    ]
                )
                
                # Extract text from response
                response_text = response.content[0].text if response.content else ""
                
                # Claude 4 wraps JSON in ```json code blocks
                if response_text.strip().startswith("```json"):
                    response_text = response_text.strip()[7:]  # Remove ```json
                    if response_text.endswith("```"):
                        response_text = response_text[:-3]  # Remove closing ```
                
                result = json.loads(response_text.strip())
            
            if result.get("has_contradiction", False):
                return Contradiction(
                    doc1_id=chapter1.get_id(),
                    doc2_id=chapter2.get_id(),
                    doc1_excerpt=result.get("doc1_excerpt", ""),
                    doc2_excerpt=result.get("doc2_excerpt", ""),
                    contradiction_type=result.get("contradiction_type", "unknown"),
                    explanation=result.get("explanation", ""),
                    confidence_score=result.get("confidence_score", 0.5)
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting contradiction: {e}")
            return None


class ReportGenerator:
    """Generates contradiction reports in various formats"""
    
    def save_intermediate_results(self, contradictions: List[Contradiction], output_path: str = "contradictions_interim.json"):
        """Save intermediate results during processing"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "status": "in_progress",
            "total_contradictions": len(contradictions),
            "contradictions": [
                {
                    "doc1_id": c.doc1_id,
                    "doc2_id": c.doc2_id,
                    "type": c.contradiction_type,
                    "confidence": c.confidence_score,
                    "doc1_excerpt": c.doc1_excerpt,
                    "doc2_excerpt": c.doc2_excerpt,
                    "explanation": c.explanation
                }
                for c in contradictions
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
    
    def generate_json_report(self, contradictions: List[Contradiction], output_path: str = "contradictions.json"):
        """Generate JSON report of contradictions"""
        report_data = {
            "generated_at": datetime.now().isoformat(),
            "total_contradictions": len(contradictions),
            "contradictions": [
                {
                    "doc1_id": c.doc1_id,
                    "doc2_id": c.doc2_id,
                    "type": c.contradiction_type,
                    "confidence": c.confidence_score,
                    "doc1_excerpt": c.doc1_excerpt,
                    "doc2_excerpt": c.doc2_excerpt,
                    "explanation": c.explanation
                }
                for c in contradictions
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report saved to {output_path}")
    
    def generate_markdown_report(self, contradictions: List[Contradiction], chapters: Dict[str, Chapter], 
                                output_path: str = "contradictions_report.md"):
        """Generate Markdown report of contradictions"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# Book Contradiction Analysis Report\n\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Total contradictions found: {len(contradictions)}\n\n")
            
            if not contradictions:
                f.write("✅ No contradictions detected in the analyzed chapters.\n")
            else:
                f.write("## Detected Contradictions\n\n")
                
                for i, contradiction in enumerate(contradictions, 1):
                    chapter1 = chapters.get(contradiction.doc1_id)
                    chapter2 = chapters.get(contradiction.doc2_id)
                    
                    f.write(f"### Contradiction {i}\n\n")
                    f.write(f"**Type:** {contradiction.contradiction_type.title()}\n")
                    f.write(f"**Confidence:** {contradiction.confidence_score:.2f}\n\n")
                    
                    if chapter1:
                        f.write(f"**Chapter {chapter1.chapter_number}** (Pages {chapter1.page_start}-{chapter1.page_end}):\n")
                        f.write(f"> {contradiction.doc1_excerpt}\n\n")
                    
                    if chapter2:
                        f.write(f"**Chapter {chapter2.chapter_number}** (Pages {chapter2.page_start}-{chapter2.page_end}):\n")
                        f.write(f"> {contradiction.doc2_excerpt}\n\n")
                    
                    f.write(f"**Explanation:** {contradiction.explanation}\n\n")
                    f.write("---\n\n")
        
        logger.info(f"Markdown report saved to {output_path}")
    
    def print_summary(self, contradictions: List[Contradiction]):
        """Print summary to console with colors"""
        print(f"\n{Fore.CYAN}=== Contradiction Analysis Summary ==={Style.RESET_ALL}\n")
        
        if not contradictions:
            print(f"{Fore.GREEN}✅ No contradictions found!{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}⚠️  Found {len(contradictions)} contradiction(s){Style.RESET_ALL}\n")
            
            # Group by type
            by_type = {}
            for c in contradictions:
                by_type.setdefault(c.contradiction_type, []).append(c)
            
            for type_name, items in by_type.items():
                print(f"{Fore.MAGENTA}{type_name.title()}: {len(items)} contradiction(s){Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}High confidence contradictions (>0.8):{Style.RESET_ALL}")
            high_conf = [c for c in contradictions if c.confidence_score > 0.8]
            for c in high_conf[:3]:  # Show top 3
                print(f"  • Chapters {c.doc1_id.split('_')[1]} vs {c.doc2_id.split('_')[1]}")
                print(f"    {Fore.RED}{c.explanation[:100]}...{Style.RESET_ALL}")


class RAGPDFChecker:
    """Main class orchestrating the PDF contradiction checking process"""
    
    def __init__(self, model_type="claude"):
        self.extractor = PDFChapterExtractor()
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStore()
        self.detector = ContradictionDetector(model_type=model_type)
        self.report_generator = ReportGenerator()
        self.chapters_map = {}
    
    def process_pdfs(self, pdf_folder: str = "pdf", test_mode: bool = False):
        """Process all PDFs in the specified folder"""
        pdf_files = list(Path(pdf_folder).glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {pdf_folder}")
            return
        
        print(f"\n{Fore.CYAN}Found {len(pdf_files)} PDF file(s) to process{Style.RESET_ALL}")
        
        # Extract chapters from all PDFs
        all_chapters = []
        for pdf_path in tqdm(pdf_files, desc="Extracting chapters"):
            chapters = self.extractor.extract_chapters(str(pdf_path))
            all_chapters.extend(chapters)
        
        print(f"\n{Fore.GREEN}Extracted {len(all_chapters)} chapters total{Style.RESET_ALL}")
        
        # Generate embeddings and store in vector DB
        print(f"\n{Fore.CYAN}Generating embeddings and storing in vector database...{Style.RESET_ALL}")
        for chapter in tqdm(all_chapters, desc="Processing chapters"):
            # Get chapter summary for better embedding
            summary = self._get_chapter_summary(chapter)
            embedding = self.embedding_manager.get_embedding(summary)
            self.vector_store.add_chapter(chapter, embedding)
            self.chapters_map[chapter.get_id()] = chapter
        
        # Detect contradictions
        print(f"\n{Fore.CYAN}Analyzing chapters for contradictions...{Style.RESET_ALL}")
        contradictions = self._detect_all_contradictions(all_chapters, test_mode=test_mode)
        
        # Generate reports
        self.report_generator.generate_json_report(contradictions)
        self.report_generator.generate_markdown_report(contradictions, self.chapters_map)
        self.report_generator.print_summary(contradictions)
        
        return contradictions
    
    def _get_chapter_summary(self, chapter: Chapter) -> str:
        """Get a summary of chapter content for better embedding"""
        # Use first 3000 characters as summary
        # In production, you might want to use LLM to generate actual summary
        return f"Chapter {chapter.chapter_number}: {chapter.title}\n\n{chapter.content[:3000]}"
    
    def _detect_all_contradictions(self, chapters: List[Chapter], test_mode: bool = False) -> List[Contradiction]:
        """Detect contradictions between all chapter pairs"""
        contradictions = []
        total_pairs = len(chapters) * (len(chapters) - 1) // 2
        
        # In test mode, only check first 5 pairs
        if test_mode:
            total_pairs = min(5, total_pairs)
        
        # Add rate limiting configuration
        api_calls_count = 0
        api_calls_per_minute = 10  # More conservative limit
        pairs_checked = 0
        
        with tqdm(total=total_pairs, desc="Checking chapter pairs") as pbar:
            for i in range(len(chapters)):
                for j in range(i + 1, len(chapters)):
                    # Stop if we've checked enough pairs in test mode
                    if test_mode and pairs_checked >= 5:
                        break
                    
                    # Rate limiting
                    if api_calls_count > 0 and api_calls_count % api_calls_per_minute == 0:
                        print(f"\n{Fore.YELLOW}Rate limit pause - waiting 60 seconds...{Style.RESET_ALL}")
                        time.sleep(60)
                    
                    try:
                        contradiction = self.detector.detect_contradiction(chapters[i], chapters[j])
                        if contradiction and contradiction.confidence_score > 0.6:
                            contradictions.append(contradiction)
                            print(f"\n{Fore.RED}Found contradiction between chapters {chapters[i].chapter_number} and {chapters[j].chapter_number}{Style.RESET_ALL}")
                            
                            # Save intermediate results
                            self.report_generator.save_intermediate_results(contradictions)
                    except Exception as e:
                        logger.error(f"Error checking chapters {i} and {j}: {e}")
                    
                    api_calls_count += 1
                    pairs_checked += 1
                    pbar.update(1)
                    
                    # Delay between calls to avoid rate limiting
                    time.sleep(2)  # Increased delay
                
                if test_mode and pairs_checked >= 5:
                    break
        
        return contradictions


def main():
    """Main entry point"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}RAG PDF Checker - Book Contradiction Detector{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    # Check for command line arguments
    import sys
    test_mode = "--test" in sys.argv
    
    # Determine model type (default is Claude)
    if "--openai" in sys.argv or "--gpt" in sys.argv:
        model_type = "openai"
        model_name = "GPT-4o"
    else:
        model_type = "claude"
        model_name = "Claude Sonnet 4"
    
    print(f"{Fore.YELLOW}Using {model_name} model{Style.RESET_ALL}")
    
    # Check for required environment variables
    if model_type == "openai" and not os.getenv("OPENAI_API_KEY"):
        print(f"{Fore.RED}❌ Error: OPENAI_API_KEY not found in environment variables{Style.RESET_ALL}")
        print("Please create a .env file with your OpenAI API key")
        return
    elif model_type == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        print(f"{Fore.RED}❌ Error: ANTHROPIC_API_KEY not found in environment variables{Style.RESET_ALL}")
        print("Please create a .env file with your Anthropic API key")
        return
    
    # Initialize and run the checker
    checker = RAGPDFChecker(model_type=model_type)
    
    try:
        # Start Qdrant if not running (optional - assumes Docker)
        print(f"{Fore.YELLOW}Note: Make sure Qdrant is running locally on port 6345{Style.RESET_ALL}")
        print("You can start it with: docker-compose up -d\n")
        
        if test_mode:
            print(f"{Fore.YELLOW}Running in TEST MODE - will only check first 5 chapter pairs{Style.RESET_ALL}\n")
        
        # Process PDFs
        checker.process_pdfs(test_mode=test_mode)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")


if __name__ == "__main__":
    main() 