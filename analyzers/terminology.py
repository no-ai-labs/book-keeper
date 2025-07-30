"""Terminology consistency analyzer for Book Keeper v2"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Tuple
import re
from collections import defaultdict, Counter
from .base import BaseAnalyzer, AnalysisResult

@dataclass
class TermInconsistency:
    """Represents a terminology inconsistency"""
    term_variations: List[str]  # e.g., ["유스케이스", "UseCase", "use case", "사용 사례"]
    canonical_term: str  # Recommended term
    chapters_usage: Dict[str, List[str]]  # chapter_id -> list of variations used
    severity: str  # high, medium, low
    explanation: str

class TerminologyAnalyzer(BaseAnalyzer):
    """Analyzer for terminology consistency"""
    
    def __init__(self, model_type: str = "claude"):
        super().__init__(model_type)
        
        # Common software engineering terms and their variations
        self.term_mappings = {
            "usecase": ["usecase", "use case", "use-case", "유스케이스", "사용사례", "사용 사례"],
            "entity": ["entity", "entities", "엔티티", "엔터티", "개체"],
            "repository": ["repository", "repo", "리포지토리", "레포지토리", "저장소"],
            "controller": ["controller", "컨트롤러", "제어기"],
            "gateway": ["gateway", "게이트웨이", "관문"],
            "presenter": ["presenter", "프레젠터", "표시기"],
            "dto": ["dto", "data transfer object", "데이터 전송 객체"],
            "framework": ["framework", "프레임워크", "프레임웍"],
            "driver": ["driver", "드라이버"],
            "layer": ["layer", "계층", "레이어"],
            "architecture": ["architecture", "아키텍처", "아키텍쳐", "구조"],
            "clean architecture": ["clean architecture", "클린 아키텍처", "클린 아키텍쳐", "깨끗한 아키텍처"],
            "dependency": ["dependency", "의존성", "의존관계", "종속성"],
            "interface": ["interface", "인터페이스", "접점"],
            "adapter": ["adapter", "adaptor", "어댑터", "어뎁터", "변환기"],
            "business logic": ["business logic", "비즈니스 로직", "업무 로직", "비지니스 로직"],
            "domain": ["domain", "도메인", "영역"],
            "application": ["application", "애플리케이션", "어플리케이션", "응용", "앱"],
            "persistence": ["persistence", "영속성", "지속성", "퍼시스턴스"],
            "database": ["database", "db", "데이터베이스", "디비"],
            "api": ["api", "API", "에이피아이"],
            "crud": ["crud", "CRUD"],
            "rest": ["rest", "REST", "레스트"],
            "http": ["http", "HTTP"],
            "json": ["json", "JSON", "제이슨"],
            "request": ["request", "요청", "리퀘스트"],
            "response": ["response", "응답", "리스폰스"],
            "client": ["client", "클라이언트", "고객"],
            "server": ["server", "서버"],
            "service": ["service", "서비스"],
            "component": ["component", "컴포넌트", "구성요소", "구성 요소"],
            "module": ["module", "모듈"],
            "package": ["package", "패키지"],
            "class": ["class", "클래스"],
            "method": ["method", "메서드", "메소드", "함수"],
            "function": ["function", "함수", "펑션"],
            "parameter": ["parameter", "파라미터", "매개변수", "인자"],
            "return": ["return", "반환", "리턴"],
            "exception": ["exception", "예외", "익셉션"],
            "error": ["error", "에러", "오류"],
            "test": ["test", "테스트"],
            "unit test": ["unit test", "단위 테스트", "유닛 테스트"],
            "integration test": ["integration test", "통합 테스트"],
            "mock": ["mock", "목", "모의 객체"],
            "stub": ["stub", "스텁"],
            "design pattern": ["design pattern", "디자인 패턴", "설계 패턴"],
            "singleton": ["singleton", "싱글톤", "싱글턴"],
            "factory": ["factory", "팩토리", "공장"],
            "observer": ["observer", "옵저버", "관찰자"],
            "strategy": ["strategy", "전략", "스트래티지"],
            "solid": ["solid", "SOLID", "솔리드"],
            "dry": ["dry", "DRY", "중복배제"],
            "kiss": ["kiss", "KISS", "단순성"],
            "abstraction": ["abstraction", "추상화", "추상"],
            "encapsulation": ["encapsulation", "캡슐화", "은닉"],
            "inheritance": ["inheritance", "상속"],
            "polymorphism": ["polymorphism", "다형성"],
            "coupling": ["coupling", "결합도", "커플링"],
            "cohesion": ["cohesion", "응집도", "응집력"],
            "refactoring": ["refactoring", "리팩토링", "리팩터링"],
            "code smell": ["code smell", "코드 스멜", "코드 냄새"],
            "technical debt": ["technical debt", "기술 부채", "기술적 부채"],
            "boundary": ["boundary", "경계", "바운더리"],
            "port": ["port", "포트"],
            "adapter pattern": ["adapter pattern", "어댑터 패턴", "변환기 패턴"],
            "hexagonal architecture": ["hexagonal architecture", "육각형 아키텍처", "헥사고날 아키텍처"],
            "onion architecture": ["onion architecture", "양파 아키텍처", "어니언 아키텍처"],
            "microservice": ["microservice", "마이크로서비스", "마이크로 서비스"],
            "monolith": ["monolith", "모놀리스", "단일체"],
            "separation of concerns": ["separation of concerns", "관심사 분리", "관심사의 분리"],
            "single responsibility": ["single responsibility", "단일 책임", "단일책임"],
            "open closed": ["open closed", "개방 폐쇄", "개방-폐쇄"],
            "liskov substitution": ["liskov substitution", "리스코프 치환", "리스코브 치환"],
            "interface segregation": ["interface segregation", "인터페이스 분리", "인터페이스 격리"],
            "dependency inversion": ["dependency inversion", "의존성 역전", "의존 역전", "의존관계 역전"]
        }
    
    def _create_prompt(self, chapter1: Any, chapter2: Any) -> str:
        """Create prompt for terminology consistency check"""
        prompt = f"""Analyze terminology consistency between two chapters in Korean software engineering books.

Chapter 1 (ID: {chapter1.get_id()}):
{chapter1.text[:3000]}

Chapter 2 (ID: {chapter2.get_id()}):
{chapter2.text[:3000]}

Find terminology inconsistencies and respond in JSON format:
{{
    "inconsistencies": [
        {{
            "concept": "the actual concept being described",
            "terms_found": ["list", "of", "different", "terms", "used"],
            "recommended_term": "most appropriate term to use",
            "severity": "high|medium|low",
            "examples": [
                {{
                    "chapter_id": "chapter id",
                    "term_used": "actual term used",
                    "context": "sentence where the term appears"
                }}
            ],
            "explanation": "왜 이 용어들이 통일되어야 하는지 한글로 설명"
        }}
    ],
    "consistency_score": 0.0-1.0
}}

Consider:
1. Same concept referred to with different terms
2. Mixed use of English/Korean for same concept
3. Inconsistent translations
4. Abbreviations vs full terms
5. Formal vs informal terminology

IMPORTANT: The 'explanation' field MUST be written in Korean (한글).
"""
        return prompt
    
    def get_analyzer_name(self) -> str:
        """Return the name of this analyzer"""
        return "terminology"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Get the analysis prompt - uses _create_prompt internally"""
        chapter1 = context.get('chapter1')
        chapter2 = context.get('chapter2')
        if chapter1 and chapter2:
            return self._create_prompt(chapter1, chapter2)
        return ""
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze terminology consistency across all chapters"""
        self.logger.info("Analyzing terminology consistency...")
        
        # First, extract all terms from chapters
        chapter_terms = self._extract_terms_from_chapters(chapters)
        
        # Find inconsistencies using both pattern matching and LLM
        all_inconsistencies = []
        
        # Pattern-based detection
        pattern_inconsistencies = self._detect_pattern_inconsistencies(chapter_terms)
        all_inconsistencies.extend(pattern_inconsistencies)
        
        # LLM-based detection for more complex cases
        total_pairs = 0
        for i in range(len(chapters)):
            for j in range(i + 1, len(chapters)):
                if total_pairs >= 10:  # Limit to avoid too many API calls
                    break
                    
                llm_inconsistencies = self._analyze_chapter_pair_terminology(
                    chapters[i], chapters[j]
                )
                all_inconsistencies.extend(llm_inconsistencies)
                total_pairs += 1
            
            if total_pairs >= 10:
                break
        
        # Calculate consistency score
        total_terms = sum(len(terms) for terms in chapter_terms.values())
        inconsistent_terms = len(all_inconsistencies)
        consistency_score = 1.0 - (inconsistent_terms / max(total_terms, 1))
        
        return AnalysisResult(
            analyzer_type="terminology",
            total_issues=len(all_inconsistencies),
            confidence_score=consistency_score,
            details={"inconsistencies": [self._inconsistency_to_dict(inc) for inc in all_inconsistencies]},
            summary={
                "total_inconsistencies": len(all_inconsistencies),
                "high_severity": len([i for i in all_inconsistencies if i.severity == "high"]),
                "most_inconsistent_terms": self._get_most_inconsistent_terms(all_inconsistencies),
                "recommendations": self._generate_recommendations(all_inconsistencies)
            }
        )
    
    def _extract_terms_from_chapters(self, chapters: List[Any]) -> Dict[str, Set[str]]:
        """Extract technical terms from each chapter"""
        chapter_terms = {}
        
        for chapter in chapters:
            terms = set()
            text_lower = chapter.text.lower()
            
            # Extract based on known term mappings
            for concept, variations in self.term_mappings.items():
                for variation in variations:
                    if variation.lower() in text_lower:
                        terms.add(variation)
            
            # Extract CamelCase terms
            camelcase_pattern = r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b'
            camelcase_terms = re.findall(camelcase_pattern, chapter.text)
            terms.update(camelcase_terms)
            
            # Extract Korean technical terms (ending with common suffixes)
            korean_tech_pattern = r'[가-힣]+(?:화|성|도|층|기|체|자)\b'
            korean_terms = re.findall(korean_tech_pattern, chapter.text)
            terms.update(korean_terms)
            
            chapter_terms[chapter.get_id()] = terms
        
        return chapter_terms
    
    def _detect_pattern_inconsistencies(self, chapter_terms: Dict[str, Set[str]]) -> List[TermInconsistency]:
        """Detect inconsistencies using pattern matching"""
        inconsistencies = []
        
        # Check each concept in term mappings
        for concept, variations in self.term_mappings.items():
            chapters_usage = defaultdict(list)
            
            # Find which variations are used in which chapters
            for chapter_id, terms in chapter_terms.items():
                for term in terms:
                    if term.lower() in [v.lower() for v in variations]:
                        chapters_usage[chapter_id].append(term)
            
            # If multiple variations are used across chapters, it's an inconsistency
            unique_variations = set()
            for terms_list in chapters_usage.values():
                unique_variations.update(terms_list)
            
            if len(unique_variations) > 1:
                # Determine canonical term (prefer Korean for Korean books)
                canonical = self._determine_canonical_term(list(unique_variations))
                
                inconsistencies.append(TermInconsistency(
                    term_variations=list(unique_variations),
                    canonical_term=canonical,
                    chapters_usage=dict(chapters_usage),
                    severity=self._determine_severity(unique_variations),
                    explanation=f"'{concept}' 개념이 여러 용어로 혼용되고 있습니다. 일관성을 위해 '{canonical}' 사용을 권장합니다."
                ))
        
        return inconsistencies
    
    def _analyze_chapter_pair_terminology(self, chapter1: Any, chapter2: Any) -> List[TermInconsistency]:
        """Use LLM to find terminology inconsistencies between chapters"""
        prompt = self._create_prompt(chapter1, chapter2)
        
        try:
            if self.model_type == "claude":
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0,
                    system="You are a technical documentation analyzer specializing in terminology consistency.",
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.content[0].text
            else:  # OpenAI
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a technical documentation analyzer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    response_format={"type": "json_object"}
                )
                response_text = response.choices[0].message.content
            
            result = self.parse_llm_response(response_text)
            
            inconsistencies = []
            for inc_data in result.get('inconsistencies', []):
                # Map to our data structure
                chapters_usage = defaultdict(list)
                for example in inc_data.get('examples', []):
                    chapters_usage[example['chapter_id']].append(example['term_used'])
                
                inconsistencies.append(TermInconsistency(
                    term_variations=inc_data.get('terms_found', []),
                    canonical_term=inc_data.get('recommended_term', ''),
                    chapters_usage=dict(chapters_usage),
                    severity=inc_data.get('severity', 'medium'),
                    explanation=inc_data.get('explanation', '')
                ))
            
            return inconsistencies
            
        except Exception as e:
            self.logger.error(f"Error analyzing terminology: {e}")
            return []
    
    def _determine_canonical_term(self, variations: List[str]) -> str:
        """Determine the best canonical term from variations"""
        # Prefer Korean terms for Korean books
        korean_terms = [t for t in variations if any(ord(c) >= 0xAC00 and ord(c) <= 0xD7A3 for c in t)]
        if korean_terms:
            # Prefer formal/standard Korean terms
            for term in korean_terms:
                if term in ["유스케이스", "엔티티", "컨트롤러", "리포지토리", "프레젠터"]:
                    return term
            return korean_terms[0]
        
        # Otherwise, prefer standard English terms
        english_terms = [t for t in variations if t[0].isupper()]
        if english_terms:
            return english_terms[0]
        
        return variations[0]
    
    def _determine_severity(self, variations: Set[str]) -> str:
        """Determine severity of terminology inconsistency"""
        # High severity: Core architectural terms
        high_severity_concepts = {
            "usecase", "entity", "controller", "repository", 
            "clean architecture", "dependency", "layer"
        }
        
        for concept, terms in self.term_mappings.items():
            if any(v.lower() in [t.lower() for t in terms] for v in variations):
                if concept in high_severity_concepts:
                    return "high"
        
        # Medium severity: Important but not core terms
        if len(variations) > 2:
            return "medium"
        
        return "low"
    
    def _get_most_inconsistent_terms(self, inconsistencies: List[TermInconsistency]) -> List[str]:
        """Get the most problematic terms"""
        term_counts = Counter()
        for inc in inconsistencies:
            term_counts[inc.canonical_term] += len(inc.term_variations)
        
        return [term for term, _ in term_counts.most_common(5)]
    
    def _generate_recommendations(self, inconsistencies: List[TermInconsistency]) -> List[str]:
        """Generate recommendations for terminology consistency"""
        recommendations = []
        
        if any(i.severity == "high" for i in inconsistencies):
            recommendations.append("핵심 아키텍처 용어의 통일이 시급합니다. 용어집을 만들어 일관성을 유지하세요.")
        
        # Find most common inconsistency patterns
        eng_kor_mix = sum(1 for i in inconsistencies 
                         if any(ord(c) < 128 for c in i.term_variations[0]) and 
                            any(ord(c) >= 0xAC00 for c in i.term_variations[0]))
        
        if eng_kor_mix > 3:
            recommendations.append("영어/한글 용어가 혼용되고 있습니다. 독자층을 고려하여 일관된 언어를 선택하세요.")
        
        # Check for informal terms
        informal_count = sum(1 for i in inconsistencies 
                           if any(term in ["디비", "앱", "레포"] for term in i.term_variations))
        
        if informal_count > 0:
            recommendations.append("비공식적인 약어 사용을 자제하고 정식 용어를 사용하세요.")
        
        return recommendations
    
    def _inconsistency_to_dict(self, inconsistency: TermInconsistency) -> Dict[str, Any]:
        """Convert TermInconsistency to dictionary"""
        return {
            "term_variations": inconsistency.term_variations,
            "canonical_term": inconsistency.canonical_term,
            "chapters_usage": inconsistency.chapters_usage,
            "severity": inconsistency.severity,
            "explanation": inconsistency.explanation
        } 