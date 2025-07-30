#!/usr/bin/env python3
"""
Book Keeper v2.0 - Comprehensive PDF Quality Analyzer
"""

import os
import sys
import json
import logging
import argparse
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

# Import existing modules
from pdfplumber import PDF
import pdfplumber
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from openai import OpenAI
from tqdm import tqdm
from colorama import init, Fore, Style
from dotenv import load_dotenv

# Import analyzers
from analyzers import (
    ContradictionAnalyzer,
    FlowAnalyzer,
    RedundancyAnalyzer,
    CodeAnalyzer,
    TheoryAnalyzer,
    TerminologyAnalyzer
)

# Initialize colorama
init(autoreset=True)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('book_keeper_v2.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class Chapter:
    """Represents a chapter extracted from PDF"""
    file_name: str
    file_hash: str
    chapter_number: int
    title: str
    text: str
    page_start: int
    page_end: int
    
    def get_id(self) -> str:
        """Generate unique chapter ID"""
        return f"{self.file_hash[:8]}_{self.chapter_number}"

@dataclass
class ComprehensiveReport:
    """Comprehensive quality analysis report"""
    generated_at: str
    total_chapters: int
    check_types: List[str]
    
    # Analysis results
    contradictions: Optional[List[Dict[str, Any]]] = None
    flow_issues: Optional[List[Dict[str, Any]]] = None
    redundancies: Optional[List[Dict[str, Any]]] = None
    code_errors: Optional[List[Dict[str, Any]]] = None
    theory_deviations: Optional[List[Dict[str, Any]]] = None
    terminology_inconsistencies: Optional[List[Dict[str, Any]]] = None
    
    # Overall scores
    overall_score: float = 0.0
    subscores: Dict[str, float] = field(default_factory=dict)
    
    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)

class PDFChapterExtractor:
    """Extract chapters from PDF files"""
    
    CHAPTER_PATTERNS = [
        r'(?:Chapter|CHAPTER)\s+(\d+)',
        r'제?\s*(\d+)\s*장',
        r'^(\d+)\.\s+',
        r'PART\s+(\d+)'
    ]
    
    def extract_chapters(self, pdf_path: str) -> List[Chapter]:
        """Extract chapters from a PDF file"""
        chapters = []
        file_name = os.path.basename(pdf_path)
        file_hash = self._generate_file_hash(pdf_path)
        
        with pdfplumber.open(pdf_path) as pdf:
            current_chapter = None
            chapter_text = []
            chapter_start_page = 0
            
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                
                # Check for chapter markers
                chapter_match = self._find_chapter_marker(text)
                
                if chapter_match:
                    # Save previous chapter if exists
                    if current_chapter is not None:
                        chapters.append(Chapter(
                            file_name=file_name,
                            file_hash=file_hash,
                            chapter_number=current_chapter['number'],
                            title=current_chapter['title'],
                            text='\n'.join(chapter_text),
                            page_start=chapter_start_page,
                            page_end=page_num - 1
                        ))
                    
                    # Start new chapter
                    current_chapter = chapter_match
                    chapter_text = [text]
                    chapter_start_page = page_num
                else:
                    # Continue current chapter
                    chapter_text.append(text)
            
            # Save last chapter
            if current_chapter is not None:
                chapters.append(Chapter(
                    file_name=file_name,
                    file_hash=file_hash,
                    chapter_number=current_chapter['number'],
                    title=current_chapter['title'],
                    text='\n'.join(chapter_text),
                    page_start=chapter_start_page,
                    page_end=len(pdf.pages) - 1
                ))
        
        return chapters
    
    def _find_chapter_marker(self, text: str) -> Optional[Dict[str, Any]]:
        """Find chapter markers in text"""
        import re
        
        lines = text.split('\n')[:10]  # Check first 10 lines
        
        for line in lines:
            for pattern in self.CHAPTER_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    return {
                        'number': int(match.group(1)),
                        'title': line.strip()
                    }
        return None
    
    def _generate_file_hash(self, file_path: str) -> str:
        """Generate hash for file identification"""
        import hashlib
        return hashlib.md5(file_path.encode()).hexdigest()

class VectorStore:
    """Manage vector embeddings in Qdrant"""
    
    def __init__(self, host: str = "localhost", port: int = 6345, collection_name: str = "book_keeper_v2"):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self._ensure_collection()
    
    def _ensure_collection(self):
        """Ensure collection exists"""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )
    
    def add_chapter(self, chapter: Chapter, embedding: List[float]):
        """Add chapter with embedding to vector store"""
        point_id = hash(chapter.get_id()) % (10 ** 8)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "chapter_id": chapter.get_id(),
                        "file_name": chapter.file_name,
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                        "text_preview": chapter.text[:500]
                    }
                )
            ]
        )

class EmbeddingManager:
    """Manage text embeddings"""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.client = OpenAI()
        self.model = model
        self.embedding_dim = 1536  # text-embedding-3-small dimension
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding for text"""
        response = self.client.embeddings.create(
            model=self.model,
            input=text[:8000]  # Limit text length
        )
        return response.data[0].embedding

class QualityChecker:
    """Main quality checker orchestrator for v2.0"""
    
    def __init__(self, model_type: str = "claude"):
        self.model_type = model_type
        self.analyzers = {
            'contradiction': ContradictionAnalyzer(model_type),
            'flow': FlowAnalyzer(model_type),
            'redundancy': RedundancyAnalyzer(model_type),
            'code': CodeAnalyzer(model_type),
            'theory': TheoryAnalyzer(model_type),
            'terminology': TerminologyAnalyzer(model_type)
        }
        self.logger = logger
    
    def check(self, chapters: List[Chapter], 
              check_types: Optional[List[str]] = None,
              test_mode: bool = False) -> ComprehensiveReport:
        """
        Run quality checks on chapters
        
        Args:
            chapters: List of chapters to analyze
            check_types: Specific checks to run. None means all checks (comprehensive)
            test_mode: If True, limit analysis scope for testing
        """
        if check_types is None:
            check_types = list(self.analyzers.keys())
        
        self.logger.info(f"Running quality checks: {', '.join(check_types)}")
        
        # Limit scope in test mode
        if test_mode:
            chapters = chapters[:3]  # Only first 3 chapters
            self.logger.info("Test mode: Analyzing only first 3 chapters")
        
        results = {}
        subscores = {}
        
        # Run selected analyzers
        for check_type in check_types:
            if check_type in self.analyzers:
                self.logger.info(f"Running {check_type} analysis...")
                analyzer = self.analyzers[check_type]
                
                # Special handling for redundancy in test mode
                if check_type == 'redundancy' and test_mode:
                    # Limit redundancy checks in test mode
                    limited_chapters = chapters[:2]
                    result = analyzer.analyze(limited_chapters)
                else:
                    result = analyzer.analyze(chapters)
                
                # Store results
                if check_type == 'terminology':
                    # Terminology returns details as dict with 'inconsistencies' key
                    results[check_type] = result.details.get('inconsistencies', [])
                else:
                    results[check_type] = result.details
                subscores[check_type] = result.confidence_score
                
                # Log summary
                self.logger.info(f"{check_type.capitalize()}: {result.summary}")
        
        # Calculate overall score
        overall_score = sum(subscores.values()) / len(subscores) if subscores else 0.0
        
        # Create summary
        summary = self._create_summary(results, subscores)
        
        # Build report
        report = ComprehensiveReport(
            generated_at=datetime.now().isoformat(),
            total_chapters=len(chapters),
            check_types=check_types,
            overall_score=overall_score,
            subscores=subscores,
            summary=summary
        )
        
        # Add specific results
        if 'contradiction' in results:
            report.contradictions = results['contradiction']
        if 'flow' in results:
            report.flow_issues = results['flow']
        if 'redundancy' in results:
            report.redundancies = results['redundancy']
        if 'code' in results:
            report.code_errors = results['code']
        if 'theory' in results:
            report.theory_deviations = results['theory']
        if 'terminology' in results:
            report.terminology_inconsistencies = results['terminology']
        
        return report
    
    def _create_summary(self, results: Dict[str, List[Dict]], 
                       subscores: Dict[str, float]) -> Dict[str, Any]:
        """Create analysis summary"""
        summary = {
            "total_issues": sum(len(issues) for issues in results.values()),
            "issues_by_type": {k: len(v) for k, v in results.items()},
            "quality_assessment": self._get_quality_assessment(subscores)
        }
        
        # Add specific insights
        insights = []
        
        if 'contradiction' in results and results['contradiction']:
            insights.append(f"Found {len(results['contradiction'])} logical contradictions")
        
        if 'flow' in results and results['flow']:
            flow_issues = results['flow']
            high_severity = len([f for f in flow_issues if f.get('severity') == 'high'])
            if high_severity > 0:
                insights.append(f"{high_severity} high-severity flow issues detected")
        
        if 'code' in results and results['code']:
            code_errors = results['code']
            syntax_errors = len([e for e in code_errors if e.get('error_type') == 'syntax'])
            if syntax_errors > 0:
                insights.append(f"{syntax_errors} syntax errors in code examples")
        
        if 'theory' in results and results['theory']:
            theory_issues = results['theory']
            critical = len([t for t in theory_issues if t.get('severity') == 'critical'])
            if critical > 0:
                insights.append(f"{critical} critical theoretical accuracy issues")
        
        if 'terminology' in results and results['terminology']:
            term_issues = results['terminology']
            high_severity = len([t for t in term_issues if t.get('severity') == 'high'])
            if high_severity > 0:
                insights.append(f"{high_severity} high-severity terminology inconsistencies")
            else:
                insights.append(f"Found {len(term_issues)} terminology variations")
        
        summary["key_insights"] = insights
        
        return summary
    
    def _get_quality_assessment(self, subscores: Dict[str, float]) -> str:
        """Get overall quality assessment"""
        avg_score = sum(subscores.values()) / len(subscores) if subscores else 0
        
        if avg_score >= 0.9:
            return "Excellent"
        elif avg_score >= 0.8:
            return "Good"
        elif avg_score >= 0.7:
            return "Fair"
        elif avg_score >= 0.6:
            return "Needs Improvement"
        else:
            return "Poor"

class ReportGenerator:
    """Generate various report formats"""
    
    def __init__(self):
        self.logger = logger
    
    def save_json_report(self, report: ComprehensiveReport, chapter_map: Optional[Dict] = None,
                        filename: str = "quality_report_v2.json"):
        """Save report as JSON"""
        report_dict = asdict(report)
        
        # Add chapter mapping info to report
        if chapter_map:
            report_dict['chapter_info'] = chapter_map
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"JSON report saved to {filename}")
    
    def save_markdown_report(self, report: ComprehensiveReport, chapter_map: Optional[Dict] = None,
                           filename: str = "quality_report_v2.md"):
        """Save report as Markdown"""
        lines = [
            f"# 📊 Book Keeper v2.0 - Comprehensive Quality Report",
            f"",
            f"**Generated**: {report.generated_at}",
            f"**Total Chapters Analyzed**: {report.total_chapters}",
            f"**Checks Performed**: {', '.join(report.check_types)}",
            f"",
            f"## 🎯 Overall Quality Score: {report.overall_score:.2%}",
            f"",
            f"### 📈 Subscores",
            f""
        ]
        
        for check_type, score in report.subscores.items():
            emoji = self._get_score_emoji(score)
            lines.append(f"- **{check_type.capitalize()}**: {emoji} {score:.2%}")
        
        lines.extend([
            f"",
            f"## 📋 Summary",
            f"",
            f"**Quality Assessment**: {report.summary.get('quality_assessment', 'Unknown')}",
            f"**Total Issues Found**: {report.summary.get('total_issues', 0)}",
            f""
        ])
        
        # Key insights
        if report.summary.get('key_insights'):
            lines.append("### 🔍 Key Insights")
            lines.append("")
            for insight in report.summary['key_insights']:
                lines.append(f"- {insight}")
            lines.append("")
        
        # Detailed sections
        if report.contradictions:
            lines.extend(self._format_contradictions_section(report.contradictions, chapter_map))
        
        if report.flow_issues:
            lines.extend(self._format_flow_section(report.flow_issues, chapter_map))
        
        if report.redundancies:
            lines.extend(self._format_redundancy_section(report.redundancies, chapter_map))
        
        if report.code_errors:
            lines.extend(self._format_code_section(report.code_errors, chapter_map))
        
        if report.theory_deviations:
            lines.extend(self._format_theory_section(report.theory_deviations, chapter_map))
        
        if report.terminology_inconsistencies:
            lines.extend(self._format_terminology_section(report.terminology_inconsistencies, chapter_map))
        
        # Add note at the end
        lines.extend([
            "",
            "---",
            "",
            "📌 **Note**: This summary shows all issues found. For the complete analysis with detailed explanations, please refer to:",
            "- `quality_report_v2.json` - Full JSON report with all data",
            "- The console output during analysis contains real-time progress information",
            ""
        ])
        
        # Write report
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        self.logger.info(f"Markdown report saved to {filename}")
    
    def print_summary(self, report: ComprehensiveReport):
        """Print colored summary to console"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Book Keeper v2.0 - Analysis Complete{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
        
        # Overall score with color
        score_color = self._get_score_color(report.overall_score)
        print(f"Overall Quality Score: {score_color}{report.overall_score:.2%}{Style.RESET_ALL}")
        print(f"Quality Assessment: {report.summary.get('quality_assessment', 'Unknown')}\n")
        
        # Subscores
        print(f"{Fore.YELLOW}Detailed Scores:{Style.RESET_ALL}")
        for check_type, score in report.subscores.items():
            score_color = self._get_score_color(score)
            print(f"  {check_type.capitalize()}: {score_color}{score:.2%}{Style.RESET_ALL}")
        
        print(f"\n{Fore.YELLOW}Issues Found:{Style.RESET_ALL}")
        for check_type, count in report.summary.get('issues_by_type', {}).items():
            if count > 0:
                print(f"  {check_type.capitalize()}: {Fore.RED}{count}{Style.RESET_ALL}")
        
        # Key insights
        if report.summary.get('key_insights'):
            print(f"\n{Fore.YELLOW}Key Insights:{Style.RESET_ALL}")
            for insight in report.summary['key_insights']:
                print(f"  • {insight}")
        
        print(f"\n{Fore.GREEN}✓ Reports saved:{Style.RESET_ALL}")
        print(f"  - quality_report_v2.json")
        print(f"  - quality_report_v2.md")
        print()
    
    def _get_score_color(self, score: float):
        """Get color based on score"""
        if score >= 0.9:
            return Fore.GREEN
        elif score >= 0.7:
            return Fore.YELLOW
        else:
            return Fore.RED
    
    def _get_score_emoji(self, score: float) -> str:
        """Get emoji based on score"""
        if score >= 0.9:
            return "✅"
        elif score >= 0.7:
            return "⚠️"
        else:
            return "❌"
    
    def _format_contradictions_section(self, contradictions: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format contradictions section"""
        lines = [
            "",
            "## ❌ Contradictions",
            "",
            f"Found **{len(contradictions)}** contradictions:",
            ""
        ]
        
        # Show all contradictions, not just first 5
        for i, cont in enumerate(contradictions, 1):
            doc1_id = cont.get('doc1_id', '')
            doc2_id = cont.get('doc2_id', '')
            
            # Get chapter info
            doc1_info = self._get_chapter_info(doc1_id, chapter_map)
            doc2_info = self._get_chapter_info(doc2_id, chapter_map)
            
            lines.extend([
                f"### Contradiction {i}",
                f"- **Type**: {cont.get('type', 'unknown')}",
                f"- **Documents**: {doc1_info} ↔ {doc2_info}",
                f"- **Confidence**: {cont.get('confidence', 0):.2%}",
                f"- **Explanation**: {cont.get('explanation', '')}",
                ""
            ])
            
            # Add excerpts if available
            if cont.get('doc1_excerpt'):
                lines.extend([
                    f"  **첫 번째 문서 발췌:**",
                    f"  > {cont.get('doc1_excerpt')}",
                    ""
                ])
            
            if cont.get('doc2_excerpt'):
                lines.extend([
                    f"  **두 번째 문서 발췌:**",
                    f"  > {cont.get('doc2_excerpt')}",
                    ""
                ])
        
        return lines
    
    def _format_flow_section(self, flow_issues: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format flow issues section"""
        lines = [
            "",
            "## 📊 Content Flow Issues",
            "",
            f"Found **{len(flow_issues)}** flow issues:",
            ""
        ]
        
        # Group by severity
        by_severity = {'high': [], 'medium': [], 'low': []}
        for issue in flow_issues:
            severity = issue.get('severity', 'low')
            by_severity[severity].append(issue)
        
        for severity in ['high', 'medium', 'low']:
            if by_severity[severity]:
                lines.append(f"### {severity.capitalize()} Severity ({len(by_severity[severity])})")
                lines.append("")
                
                for issue in by_severity[severity]:
                    chapter_id = issue.get('chapter_id', 'Unknown')
                    chapter_info = self._get_chapter_info(chapter_id, chapter_map)
                    
                    lines.extend([
                        f"- **Chapter**: {chapter_info}",
                        f"  - **Type**: {issue.get('type', 'unknown')}",
                        f"  - **Description**: {issue.get('description', '')}",
                        ""
                    ])
        
        return lines
    
    def _format_redundancy_section(self, redundancies: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format redundancy section"""
        lines = [
            "",
            "## 🔁 Redundancy Analysis",
            "",
            f"Found **{len(redundancies)}** redundant sections:",
            ""
        ]
        
        for i, red in enumerate(redundancies, 1):
            seg1_id = red.get('segment1_id', '')
            seg2_id = red.get('segment2_id', '')
            
            # Extract chapter IDs from segment IDs
            ch1_id = seg1_id.split('_seg')[0] if '_seg' in seg1_id else seg1_id
            ch2_id = seg2_id.split('_seg')[0] if '_seg' in seg2_id else seg2_id
            
            ch1_info = self._get_chapter_info(ch1_id, chapter_map)
            ch2_info = self._get_chapter_info(ch2_id, chapter_map)
            
            lines.extend([
                f"### Redundancy {i}",
                f"- **Sections**: {ch1_info} ({seg1_id.split('_seg')[-1] if '_seg' in seg1_id else ''}) ↔ {ch2_info} ({seg2_id.split('_seg')[-1] if '_seg' in seg2_id else ''})",
                f"- **Similarity**: {red.get('similarity', 0):.2%}",
                f"- **Type**: {red.get('type', 'unknown')}",
                f"- **Recommendation**: {red.get('recommendation', '')}",
                ""
            ])
        
        return lines
    
    def _format_code_section(self, code_errors: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format code errors section"""
        lines = [
            "",
            "## 🐛 Code Quality Issues",
            "",
            f"Found **{len(code_errors)}** code issues:",
            ""
        ]
        
        # Group by severity
        by_severity = {'error': [], 'warning': []}
        for error in code_errors:
            severity = 'error' if error.get('error_type') == 'syntax' else 'warning'
            by_severity[severity].append(error)
        
        for severity in ['error', 'warning']:
            if by_severity[severity]:
                lines.append(f"### {severity.capitalize()}s ({len(by_severity[severity])})")
                lines.append("")
                
                for error in by_severity[severity]:
                    chapter_id = error.get('chapter_id', '')
                    chapter_info = self._get_chapter_info(chapter_id, chapter_map)
                    
                    lines.extend([
                        f"- **Chapter**: {chapter_info}",
                        f"  - **Type**: {error.get('error_type', 'unknown')}",
                        f"  - **Line**: {error.get('line_number', 'N/A')}",
                        f"  - **Message**: {error.get('message', '')}",
                        ""
                    ])
        
        return lines
    
    def _format_theory_section(self, deviations: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format theory deviations section"""
        lines = [
            "",
            "## 📚 Theoretical Accuracy",
            "",
            f"Found **{len(deviations)}** deviations from standards:",
            ""
        ]
        
        # Group by severity
        by_severity = {'critical': [], 'major': [], 'minor': []}
        for dev in deviations:
            severity = dev.get('severity', 'minor')
            by_severity[severity].append(dev)
        
        for severity in ['critical', 'major', 'minor']:
            if by_severity[severity]:
                lines.append(f"### {severity.capitalize()} Issues ({len(by_severity[severity])})")
                lines.append("")
                
                for dev in by_severity[severity]:
                    chapter_id = dev.get('chapter_id', '')
                    chapter_info = self._get_chapter_info(chapter_id, chapter_map)
                    
                    lines.extend([
                        f"- **Standard Violated**: {dev.get('standard_violated', 'unknown')}",
                        f"  - **Chapter**: {chapter_info}",
                        f"  - **Explanation**: {dev.get('explanation', '')}",
                        ""
                    ])
        
        return lines

    def _format_terminology_section(self, inconsistencies: List[Dict], chapter_map: Optional[Dict]) -> List[str]:
        """Format terminology inconsistencies section"""
        lines = [
            "",
            "## 📝 Terminology Consistency",
            "",
            f"Found **{len(inconsistencies)}** terminology inconsistencies:",
            ""
        ]
        
        # Group by severity
        by_severity = {'high': [], 'medium': [], 'low': []}
        for inc in inconsistencies:
            severity = inc.get('severity', 'medium')
            by_severity[severity].append(inc)
        
        for severity in ['high', 'medium', 'low']:
            if by_severity[severity]:
                lines.append(f"### {severity.capitalize()} Severity ({len(by_severity[severity])})")
                lines.append("")
                
                for inc in by_severity[severity]:
                    term_variations = inc.get('term_variations', [])
                    canonical = inc.get('canonical_term', '')
                    chapters_usage = inc.get('chapters_usage', {})
                    
                    lines.extend([
                        f"- **Concept**: {canonical}",
                        f"  - **Variations Found**: {', '.join(term_variations)}",
                        f"  - **Explanation**: {inc.get('explanation', '')}",
                    ])
                    
                    # Show which chapters use which terms
                    if chapters_usage:
                        lines.append("  - **Usage by Chapter**:")
                        for chapter_id, terms in chapters_usage.items():
                            chapter_info = self._get_chapter_info(chapter_id, chapter_map)
                            lines.append(f"    - {chapter_info}: {', '.join(terms)}")
                    
                    lines.append("")
        
        return lines

    def _get_chapter_info(self, chapter_id: str, chapter_map: Optional[Dict]) -> str:
        """Get readable chapter information from ID"""
        if not chapter_map or chapter_id not in chapter_map:
            return chapter_id
        
        info = chapter_map[chapter_id]
        file_name = info['file_name'].replace('.pdf', '')
        title = info['title']
        chapter_num = info['chapter_number']
        
        # Remove UUID prefix from filename for readability
        if '_' in file_name:
            readable_name = '_'.join(file_name.split('_')[1:])
        else:
            readable_name = file_name
        
        # Truncate title if too long
        if title and len(title) > 50:
            title = title[:50] + "..."
        
        # Format: "filename (Chapter X)"
        return f"{readable_name} (Chapter {chapter_num})"

class BookKeeperV2:
    """Main application class for comprehensive PDF quality analysis"""
    
    def __init__(self, model_type: str = "claude", qdrant_host: str = "localhost", qdrant_port: int = 6345):
        self.logger = logger
        self.pdf_extractor = PDFChapterExtractor()
        self.embedding_manager = EmbeddingManager()
        self.vector_store = VectorStore(host=qdrant_host, port=qdrant_port)
        self.quality_checker = QualityChecker(model_type)
        self.report_generator = ReportGenerator()
        self.chapter_map = {}  # Map chapter ID to chapter info
    
    def process_pdfs(self, pdf_dir: str = "pdf", 
                     check_types: Optional[List[str]] = None,
                     test_mode: bool = False):
        """Process all PDFs in directory"""
        pdf_files = list(Path(pdf_dir).glob("*.pdf"))
        
        if not pdf_files:
            self.logger.error(f"No PDF files found in {pdf_dir}")
            return
        
        self.logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Extract chapters from all PDFs
        all_chapters = []
        for pdf_file in tqdm(pdf_files, desc="Extracting chapters"):
            chapters = self.pdf_extractor.extract_chapters(str(pdf_file))
            all_chapters.extend(chapters)
            self.logger.info(f"Extracted {len(chapters)} chapters from {pdf_file.name}")
        
        self.logger.info(f"Total chapters extracted: {len(all_chapters)}")
        
        # Create embeddings and store in vector DB
        for chapter in tqdm(all_chapters, desc="Creating embeddings"):
            embedding = self.embedding_manager.create_embedding(chapter.text)
            self.vector_store.add_chapter(chapter, embedding)
            # Store chapter mapping
            self.chapter_map[chapter.get_id()] = {
                'file_name': chapter.file_name,
                'title': chapter.title,
                'chapter_number': chapter.chapter_number
            }
        
        # Run quality checks
        report = self.quality_checker.check(
            all_chapters, 
            check_types=check_types,
            test_mode=test_mode
        )
        
        # Generate reports with chapter mapping
        self.report_generator.save_json_report(report, self.chapter_map)
        self.report_generator.save_markdown_report(report, self.chapter_map)
        self.report_generator.print_summary(report)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Book Keeper v2.0 - Comprehensive PDF Quality Analyzer"
    )
    
    # Check types
    parser.add_argument(
        '--check',
        type=str,
        default='all',
        help='Check types to run: all (default), contradiction, flow, redundancy, code, theory, or comma-separated list'
    )
    
    # Model selection
    parser.add_argument(
        '--model',
        choices=['claude', 'openai'],
        default='claude',
        help='LLM model to use (default: claude)'
    )
    parser.add_argument('--openai', action='store_true', help='Use OpenAI GPT-4o')
    parser.add_argument('--gpt', action='store_true', help='Use OpenAI GPT-4o (alias)')
    
    # Test mode
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (limited scope)'
    )
    
    # PDF directory
    parser.add_argument(
        '--pdf-dir',
        type=str,
        default='pdf',
        help='Directory containing PDF files (default: pdf)'
    )
    
    args = parser.parse_args()
    
    # Handle model selection
    if args.openai or args.gpt:
        model_type = 'openai'
    else:
        model_type = args.model
    
    # Parse check types
    if args.check == 'all':
        check_types = None  # Comprehensive
    else:
        check_types = [t.strip() for t in args.check.split(',')]
    
    # Display configuration
    print(f"\n{Fore.CYAN}Book Keeper v2.0 - Starting Analysis{Style.RESET_ALL}")
    print(f"Model: {model_type}")
    print(f"Checks: {args.check}")
    print(f"Test Mode: {args.test}")
    print(f"PDF Directory: {args.pdf_dir}\n")
    
    # Check environment
    if model_type == 'claude' and not os.getenv('ANTHROPIC_API_KEY'):
        logger.error("ANTHROPIC_API_KEY not found in environment")
        sys.exit(1)
    elif model_type == 'openai' and not os.getenv('OPENAI_API_KEY'):
        logger.error("OPENAI_API_KEY not found in environment")
        sys.exit(1)
    
    # Run analysis
    try:
        app = BookKeeperV2(model_type=model_type)
        app.process_pdfs(
            pdf_dir=args.pdf_dir,
            check_types=check_types,
            test_mode=args.test
        )
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 