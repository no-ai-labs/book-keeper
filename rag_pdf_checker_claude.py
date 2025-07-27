#!/usr/bin/env python3
"""
RAG PDF Checker - Claude 4 Version
Quick modification to use Claude 4 instead of GPT-4
"""

from rag_pdf_checker import *
from anthropic import Anthropic

# Override the ContradictionDetector class
class ContradictionDetectorClaude(ContradictionDetector):
    """Detects contradictions using Claude 4"""
    
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"
    
    def detect_contradiction(self, chapter1: Chapter, chapter2: Chapter) -> Optional[Contradiction]:
        """Detect if two chapters contain contradictions"""
        
        # Parse chapter info to avoid confusion
        ch1_parts = chapter1.chapter_number.split('_')
        ch2_parts = chapter2.chapter_number.split('_')
        
        # Extract main document name and section
        ch1_main = ch1_parts[0] if ch1_parts else "Document"
        ch1_section = ch1_parts[-1] if len(ch1_parts) > 1 and ch1_parts[-1].isdigit() else ""
        ch2_main = ch2_parts[0] if ch2_parts else "Document"  
        ch2_section = ch2_parts[-1] if len(ch2_parts) > 1 and ch2_parts[-1].isdigit() else ""
        
        # Create the same prompt as parent class
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
The "explanation" field MUST be written in Korean (한글).

If no contradiction is found, set has_contradiction to false and return the JSON object with empty strings for the other fields.
"""
        
        try:
            # Claude requires different format
            system_prompt = "You are an expert at analyzing technical documentation for logical consistency. You MUST provide all explanations in Korean (한글). Always respond with valid JSON format only."
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract text from response
            response_text = response.content[0].text if response.content else ""
            logger.info(f"Claude response preview: {response_text[:100]}...")
            
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


# Override RAGPDFChecker to use Claude detector
class RAGPDFCheckerClaude(RAGPDFChecker):
    """Main class using Claude 4"""
    
    def __init__(self):
        super().__init__()
        self.detector = ContradictionDetectorClaude()


if __name__ == "__main__":
    # Same main logic but using Claude version
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}RAG PDF Checker - Book Contradiction Detector{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    
    print(f"{Fore.YELLOW}Using Claude Sonnet 4 model{Style.RESET_ALL}")
    
    # Check for required environment variables
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(f"{Fore.RED}❌ Error: ANTHROPIC_API_KEY not found in environment variables{Style.RESET_ALL}")
        print("Please create a .env file with your Anthropic API key")
        sys.exit(1)
    
    # Check for command line arguments
    import sys
    test_mode = "--test" in sys.argv
    
    # Initialize and run the checker
    checker = RAGPDFCheckerClaude()
    
    try:
        # Start Qdrant if not running
        print(f"{Fore.YELLOW}Note: Make sure Qdrant is running locally on port 6345{Style.RESET_ALL}")
        print("You can start it with: docker-compose up -d\n")
        
        if test_mode:
            print(f"{Fore.YELLOW}Running in TEST MODE - will only check first 5 chapter pairs{Style.RESET_ALL}\n")
        
        # Process PDFs
        checker.process_pdfs(test_mode=test_mode)
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        print(f"\n{Fore.RED}❌ Error: {e}{Style.RESET_ALL}") 