"""
Contradiction Analyzer - Detects logical contradictions between chapters
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import time
from .base import BaseAnalyzer, AnalysisResult

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

class ContradictionAnalyzer(BaseAnalyzer):
    """Analyzer for detecting contradictions between document sections"""
    
    def get_analyzer_name(self) -> str:
        return "contradiction"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Generate contradiction detection prompt"""
        ch1_info = context['chapter1']
        ch2_info = context['chapter2']
        
        # Parse chapter info
        ch1_parts = ch1_info['id'].split('_')
        ch2_parts = ch2_info['id'].split('_')
        
        ch1_main = '_'.join(ch1_parts[:-1]) if len(ch1_parts) > 1 else ch1_parts[0]
        ch2_main = '_'.join(ch2_parts[:-1]) if len(ch2_parts) > 1 else ch2_parts[0]
        
        ch1_section = ch1_parts[-1] if len(ch1_parts) > 1 else ""
        ch2_section = ch2_parts[-1] if len(ch2_parts) > 1 else ""
        
        prompt = f"""Analyze the following two documents for logical contradictions:

First Document: {ch1_main}{f' (Section {ch1_section})' if ch1_section else ''}
{ch1_info['text'][:3000]}

Second Document: {ch2_main}{f' (Section {ch2_section})' if ch2_section else ''}
{ch2_info['text'][:3000]}

Look for:
1. Conflicting definitions or explanations
2. Opposing recommendations or best practices
3. Contradictory facts or principles
4. Inconsistent methodologies

Please respond in JSON format:
{{
    "has_contradiction": true/false,
    "doc1_excerpt": "exact quote from first document",
    "doc2_excerpt": "exact quote from second document",
    "contradiction_type": "definition|recommendation|fact|principle",
    "explanation": "모순에 대한 상세한 설명을 한글로 작성하세요.",
    "confidence_score": 0.0-1.0
}}

IMPORTANT: 
- The 'explanation' field MUST be written in Korean (한글).
- Reference documents as "첫 번째 문서" and "두 번째 문서"
- When mentioning sections, use "섹션 X" format
- Do NOT use "챕터" or "장" terminology
"""
        return prompt
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze all chapter pairs for contradictions"""
        contradictions = []
        total_pairs = len(chapters) * (len(chapters) - 1) // 2
        pairs_checked = 0
        
        self.logger.info(f"Checking {total_pairs} chapter pairs for contradictions...")
        
        for i, chapter1 in enumerate(chapters):
            for j, chapter2 in enumerate(chapters[i+1:], i+1):
                pairs_checked += 1
                
                # Rate limiting
                if pairs_checked > 1:
                    time.sleep(2)
                if pairs_checked % 10 == 0:
                    self.logger.info("Pausing for rate limit...")
                    time.sleep(60)
                
                try:
                    contradiction = self._detect_contradiction(chapter1, chapter2)
                    if contradiction:
                        contradictions.append(contradiction)
                        self.logger.info(f"Found contradiction between {chapter1.get_id()} and {chapter2.get_id()}")
                except Exception as e:
                    self.logger.error(f"Error detecting contradiction: {e}")
        
        # Calculate overall confidence
        if contradictions:
            avg_confidence = sum(c.confidence_score for c in contradictions) / len(contradictions)
        else:
            # No contradictions found is actually a good thing
            avg_confidence = 1.0  # Perfect score when no contradictions found
        
        return AnalysisResult(
            analyzer_type="contradiction",
            total_issues=len(contradictions),
            confidence_score=avg_confidence,
            details=[self._contradiction_to_dict(c) for c in contradictions],
            summary=f"Found {len(contradictions)} contradictions across {total_pairs} chapter pairs"
        )
    
    def _detect_contradiction(self, chapter1: Any, chapter2: Any) -> Optional[Contradiction]:
        """Detect contradiction between two chapters"""
        context = {
            'chapter1': {'id': chapter1.get_id(), 'text': chapter1.text},
            'chapter2': {'id': chapter2.get_id(), 'text': chapter2.text}
        }
        
        prompt = self.get_prompt(context)
        response_text = self.call_llm(prompt)
        result = self.parse_llm_response(response_text)
        
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
    
    def _contradiction_to_dict(self, contradiction: Contradiction) -> Dict[str, Any]:
        """Convert Contradiction object to dictionary"""
        return {
            "doc1_id": contradiction.doc1_id,
            "doc2_id": contradiction.doc2_id,
            "doc1_excerpt": contradiction.doc1_excerpt,
            "doc2_excerpt": contradiction.doc2_excerpt,
            "type": contradiction.contradiction_type,
            "explanation": contradiction.explanation,
            "confidence": contradiction.confidence_score
        } 