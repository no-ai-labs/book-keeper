"""
Flow Analyzer - Analyzes content flow and logical progression
"""

from typing import List, Dict, Any, Set
from dataclasses import dataclass
from .base import BaseAnalyzer, AnalysisResult

@dataclass
class FlowIssue:
    """Represents a content flow issue"""
    chapter_id: str
    issue_type: str  # missing_prerequisite, broken_sequence, unclear_progression
    description: str
    missing_concepts: List[str]
    severity: str  # high, medium, low

class FlowAnalyzer(BaseAnalyzer):
    """Analyzer for content flow and logical progression"""
    
    def get_analyzer_name(self) -> str:
        return "flow"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Generate flow analysis prompt"""
        chapters_summary = context['chapters_summary']
        
        prompt = f"""Analyze the content flow and structure of these chapters:

{chapters_summary}

Check for:
1. **Prerequisite Violations**: Terms or concepts used before being introduced
2. **Logical Progression**: Whether topics build upon each other appropriately
3. **Structural Coherence**: Clear beginning, middle, and end
4. **Dependency Issues**: Chapters that reference future content inappropriately

For each issue found, identify:
- The specific chapter where the issue occurs
- The type of flow problem
- Missing prerequisite concepts if any
- Severity of the issue (high/medium/low)

Response format:
{{
    "flow_issues": [
        {{
            "chapter_id": "chapter identifier",
            "issue_type": "missing_prerequisite|broken_sequence|unclear_progression",
            "description": "문제점을 한글로 설명하세요",
            "missing_concepts": ["concept1", "concept2"],
            "severity": "high|medium|low"
        }}
    ],
    "overall_flow_score": 0.0-1.0,
    "suggestions": ["개선 제안을 한글로 작성"]
}}

IMPORTANT: All 'description' and 'suggestions' fields MUST be written in Korean (한글).
"""
        return prompt
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze content flow across all chapters"""
        self.logger.info("Analyzing content flow...")
        
        # First, extract key concepts from each chapter
        concepts_by_chapter = self._extract_concepts_from_chapters(chapters)
        
        # Build chapters summary for LLM
        chapters_summary = self._build_chapters_summary(chapters, concepts_by_chapter)
        
        # Analyze flow
        context = {'chapters_summary': chapters_summary}
        prompt = self.get_prompt(context)
        response_text = self.call_llm(prompt)
        result = self.parse_llm_response(response_text)
        
        # Process results
        flow_issues = []
        for issue_data in result.get('flow_issues', []):
            flow_issues.append(FlowIssue(
                chapter_id=issue_data['chapter_id'],
                issue_type=issue_data['issue_type'],
                description=issue_data['description'],
                missing_concepts=issue_data.get('missing_concepts', []),
                severity=issue_data['severity']
            ))
        
        overall_score = result.get('overall_flow_score', 0.7)
        suggestions = result.get('suggestions', [])
        
        return AnalysisResult(
            analyzer_type="flow",
            total_issues=len(flow_issues),
            confidence_score=overall_score,
            details=[self._flow_issue_to_dict(fi) for fi in flow_issues],
            summary=f"Found {len(flow_issues)} flow issues. Overall flow score: {overall_score:.2f}"
        )
    
    def _extract_concepts_from_chapters(self, chapters: List[Any]) -> Dict[str, Set[str]]:
        """Extract key concepts from each chapter"""
        concepts = {}
        
        for chapter in chapters:
            # Simple concept extraction using LLM
            prompt = f"""Extract key technical concepts and terms from this chapter:

Chapter: {chapter.get_id()}
Text: {chapter.text[:2000]}

List only the important technical terms, concepts, and methodologies mentioned.
Return as JSON: {{"concepts": ["concept1", "concept2", ...]}}
"""
            try:
                response_text = self.call_llm(prompt)
                result = self.parse_llm_response(response_text)
                concepts[chapter.get_id()] = set(result.get('concepts', []))
            except Exception as e:
                self.logger.error(f"Error extracting concepts from {chapter.get_id()}: {e}")
                concepts[chapter.get_id()] = set()
        
        return concepts
    
    def _build_chapters_summary(self, chapters: List[Any], concepts: Dict[str, Set[str]]) -> str:
        """Build a summary of all chapters for flow analysis"""
        summary_parts = []
        
        for i, chapter in enumerate(chapters):
            chapter_concepts = list(concepts.get(chapter.get_id(), []))[:10]  # Top 10 concepts
            summary_parts.append(
                f"Chapter {i+1} ({chapter.get_id()}):\n"
                f"- Key concepts: {', '.join(chapter_concepts)}\n"
                f"- Preview: {chapter.text[:200]}...\n"
            )
        
        return "\n".join(summary_parts)
    
    def _flow_issue_to_dict(self, flow_issue: FlowIssue) -> Dict[str, Any]:
        """Convert FlowIssue to dictionary"""
        return {
            "chapter_id": flow_issue.chapter_id,
            "issue_type": flow_issue.issue_type,
            "description": flow_issue.description,
            "missing_concepts": flow_issue.missing_concepts,
            "severity": flow_issue.severity
        } 