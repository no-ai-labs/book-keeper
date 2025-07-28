"""
Redundancy Analyzer - Detects duplicate or unnecessarily repeated content
"""

from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from .base import BaseAnalyzer, AnalysisResult

@dataclass
class Redundancy:
    """Represents detected redundant content"""
    section1_id: str
    section2_id: str
    section1_excerpt: str
    section2_excerpt: str
    similarity_score: float
    redundancy_type: str  # exact_duplicate, paraphrase, unnecessary_repetition
    explanation: str
    recommendation: str  # keep_both, merge, remove_one

class RedundancyAnalyzer(BaseAnalyzer):
    """Analyzer for detecting redundant content"""
    
    def get_analyzer_name(self) -> str:
        return "redundancy"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Generate redundancy detection prompt"""
        segment1 = context['segment1']
        segment2 = context['segment2']
        
        prompt = f"""Analyze these text segments for redundancy:

Segment 1 ({segment1['id']}):
{segment1['text'][:1500]}

Segment 2 ({segment2['id']}):
{segment2['text'][:1500]}

Determine:
1. Similarity score (0.0-1.0)
2. Type of redundancy if any:
   - exact_duplicate: Nearly identical content
   - paraphrase: Same idea expressed differently
   - unnecessary_repetition: Repeated without adding value
   - partial_overlap: Some shared content but mostly different

Response format:
{{
    "is_redundant": true/false,
    "similarity_score": 0.0-1.0,
    "redundancy_type": "exact_duplicate|paraphrase|unnecessary_repetition|partial_overlap",
    "section1_excerpt": "relevant excerpt from segment 1",
    "section2_excerpt": "relevant excerpt from segment 2",
    "explanation": "중복 내용과 영향을 한글로 설명",
    "recommendation": "keep_both|merge|remove_one",
    "recommendation_details": "구체적인 권장사항을 한글로 설명"
}}

IMPORTANT: 'explanation' and 'recommendation_details' MUST be written in Korean (한글).
"""
        return prompt
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze all chapters for redundant content"""
        self.logger.info("Analyzing content redundancy...")
        
        redundancies = []
        total_comparisons = 0
        
        # Split chapters into smaller segments for finer analysis
        segments = self._create_segments(chapters)
        
        # Compare segments
        for i, segment1 in enumerate(segments):
            for j, segment2 in enumerate(segments[i+1:], i+1):
                # Skip if from same chapter
                if segment1['chapter_id'] == segment2['chapter_id']:
                    continue
                    
                total_comparisons += 1
                
                # Quick similarity check first
                if self._quick_similarity_check(segment1['text'], segment2['text']) > 0.3:
                    redundancy = self._detect_redundancy(segment1, segment2)
                    if redundancy and redundancy.similarity_score > 0.7:
                        redundancies.append(redundancy)
                        self.logger.info(f"Found redundancy between {segment1['id']} and {segment2['id']}")
        
        # Calculate overall redundancy score
        avg_similarity = sum(r.similarity_score for r in redundancies) / len(redundancies) if redundancies else 0.0
        redundancy_ratio = len(redundancies) / max(total_comparisons, 1)
        
        return AnalysisResult(
            analyzer_type="redundancy",
            total_issues=len(redundancies),
            confidence_score=1.0 - redundancy_ratio,  # Higher score = less redundancy
            details=[self._redundancy_to_dict(r) for r in redundancies],
            summary=f"Found {len(redundancies)} redundant sections. Redundancy ratio: {redundancy_ratio:.2%}"
        )
    
    def _create_segments(self, chapters: List[Any]) -> List[Dict[str, Any]]:
        """Split chapters into analyzable segments"""
        segments = []
        segment_size = 1000  # characters per segment
        
        for chapter in chapters:
            text = chapter.text
            chapter_id = chapter.get_id()
            
            # Split into segments
            for i in range(0, len(text), segment_size // 2):  # 50% overlap
                segment_text = text[i:i + segment_size]
                if len(segment_text) > 200:  # Minimum segment size
                    segments.append({
                        'id': f"{chapter_id}_seg{i // (segment_size // 2)}",
                        'chapter_id': chapter_id,
                        'text': segment_text,
                        'start': i,
                        'end': min(i + segment_size, len(text))
                    })
        
        return segments
    
    def _quick_similarity_check(self, text1: str, text2: str) -> float:
        """Quick similarity check using simple metrics"""
        # Simple word overlap ratio
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
            
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _detect_redundancy(self, segment1: Dict[str, Any], segment2: Dict[str, Any]) -> Optional[Redundancy]:
        """Detect redundancy between two segments using LLM"""
        context = {
            'segment1': segment1,
            'segment2': segment2
        }
        
        prompt = self.get_prompt(context)
        
        try:
            response_text = self.call_llm(prompt)
            result = self.parse_llm_response(response_text)
        except Exception as e:
            self.logger.error(f"Error detecting redundancy: {e}")
            return None
        
        if result.get('is_redundant', False) and result.get('similarity_score', 0) > 0.7:
            return Redundancy(
                section1_id=segment1['id'],
                section2_id=segment2['id'],
                section1_excerpt=result.get('section1_excerpt', ''),
                section2_excerpt=result.get('section2_excerpt', ''),
                similarity_score=result.get('similarity_score', 0.0),
                redundancy_type=result.get('redundancy_type', 'unknown'),
                explanation=result.get('explanation', ''),
                recommendation=result.get('recommendation', 'keep_both')
            )
        return None
    
    def _redundancy_to_dict(self, redundancy: Redundancy) -> Dict[str, Any]:
        """Convert Redundancy to dictionary"""
        return {
            "section1_id": redundancy.section1_id,
            "section2_id": redundancy.section2_id,
            "section1_excerpt": redundancy.section1_excerpt,
            "section2_excerpt": redundancy.section2_excerpt,
            "similarity_score": redundancy.similarity_score,
            "type": redundancy.redundancy_type,
            "explanation": redundancy.explanation,
            "recommendation": redundancy.recommendation
        } 