"""
Theory Analyzer - Verifies theoretical accuracy against known standards
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from .base import BaseAnalyzer, AnalysisResult

@dataclass
class TheoryDeviation:
    """Represents a deviation from theoretical standards"""
    chapter_id: str
    excerpt: str
    standard_violated: str  # SOLID, DRY, KISS, specific design pattern
    explanation: str
    severity: str  # critical, major, minor
    correct_approach: str

class TheoryAnalyzer(BaseAnalyzer):
    """Analyzer for theoretical accuracy and best practices"""
    
    # Known standards and patterns to check against
    STANDARDS = {
        'SOLID': [
            'Single Responsibility Principle',
            'Open/Closed Principle', 
            'Liskov Substitution Principle',
            'Interface Segregation Principle',
            'Dependency Inversion Principle'
        ],
        'Design Patterns': [
            'Singleton', 'Factory', 'Observer', 'Strategy', 'Decorator',
            'Adapter', 'Facade', 'Template Method', 'Iterator', 'Composite'
        ],
        'Principles': [
            'DRY (Don\'t Repeat Yourself)',
            'KISS (Keep It Simple, Stupid)',
            'YAGNI (You Aren\'t Gonna Need It)',
            'Separation of Concerns',
            'Law of Demeter'
        ],
        'Architecture': [
            'Clean Architecture',
            'Hexagonal Architecture',
            'Domain-Driven Design',
            'Event-Driven Architecture',
            'Microservices'
        ]
    }
    
    def get_analyzer_name(self) -> str:
        return "theory"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Generate theory verification prompt"""
        chapter = context['chapter']
        standards_list = []
        
        for category, items in self.STANDARDS.items():
            standards_list.extend(items)
        
        prompt = f"""Analyze this technical documentation for theoretical accuracy:

Chapter: {chapter['id']}
Content:
{chapter['text'][:3000]}

Check against these software engineering standards and best practices:
{', '.join(standards_list)}

Identify any:
1. Misrepresentations of design patterns
2. Violations of SOLID principles
3. Incorrect explanations of architectural concepts
4. Deviations from industry best practices
5. Contradictions with established software engineering theory

Response format:
{{
    "deviations": [
        {{
            "excerpt": "exact quote that violates standards",
            "standard_violated": "specific standard or principle",
            "explanation": "표준과의 차이점을 한글로 설명하세요",
            "severity": "critical|major|minor",
            "correct_approach": "올바른 접근 방법을 한글로 설명하세요"
        }}
    ],
    "theory_score": 0.0-1.0,
    "positive_aspects": ["잘 설명된 이론적 개념들을 한글로 나열"]
}}

IMPORTANT: 'explanation', 'correct_approach', and 'positive_aspects' MUST be written in Korean (한글).
"""
        return prompt
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze theoretical accuracy of all chapters"""
        self.logger.info("Analyzing theoretical accuracy...")
        
        all_deviations = []
        total_score = 0.0
        positive_aspects = []
        
        for chapter in chapters:
            # Analyze each chapter for theory violations
            deviations, score, positives = self._analyze_chapter_theory(chapter)
            all_deviations.extend(deviations)
            total_score += score
            positive_aspects.extend(positives)
        
        # Calculate overall theory accuracy
        avg_score = total_score / len(chapters) if chapters else 0.0
        critical_count = len([d for d in all_deviations if d.severity == 'critical'])
        major_count = len([d for d in all_deviations if d.severity == 'major'])
        
        return AnalysisResult(
            analyzer_type="theory",
            total_issues=len(all_deviations),
            confidence_score=avg_score,
            details=[self._deviation_to_dict(d) for d in all_deviations],
            summary=f"Found {critical_count} critical and {major_count} major theory deviations. Theory accuracy: {avg_score:.2f}"
        )
    
    def _analyze_chapter_theory(self, chapter: Any) -> Tuple[List[TheoryDeviation], float, List[str]]:
        """Analyze a single chapter for theoretical accuracy"""
        context = {
            'chapter': {
                'id': chapter.get_id(),
                'text': chapter.text
            }
        }
        
        prompt = self.get_prompt(context)
        response_text = self.call_llm(prompt)
        
        try:
            result = self.parse_llm_response(response_text)
        except Exception as e:
            self.logger.error(f"Error parsing theory analysis response: {e}")
            # Return empty results on parse error
            return [], 0.8, []
        
        deviations = []
        for dev_data in result.get('deviations', []):
            deviations.append(TheoryDeviation(
                chapter_id=chapter.get_id(),
                excerpt=dev_data.get('excerpt', ''),
                standard_violated=dev_data.get('standard_violated', 'unknown'),
                explanation=dev_data.get('explanation', ''),
                severity=dev_data.get('severity', 'minor'),
                correct_approach=dev_data.get('correct_approach', '')
            ))
        
        score = result.get('theory_score', 0.8)
        positives = result.get('positive_aspects', [])
        
        return deviations, score, positives
    
    def _deviation_to_dict(self, deviation: TheoryDeviation) -> Dict[str, Any]:
        """Convert TheoryDeviation to dictionary"""
        return {
            "chapter_id": deviation.chapter_id,
            "excerpt": deviation.excerpt,
            "standard_violated": deviation.standard_violated,
            "explanation": deviation.explanation,
            "severity": deviation.severity,
            "correct_approach": deviation.correct_approach
        } 