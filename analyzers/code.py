"""
Code Analyzer - Validates code snippets in documentation
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import ast
from .base import BaseAnalyzer, AnalysisResult

@dataclass
class CodeError:
    """Represents a code quality issue"""
    chapter_id: str
    code_block_index: int
    code_excerpt: str
    error_type: str  # syntax, import, undefined, logic, style
    line_number: Optional[int]
    description: str
    severity: str  # error, warning, info
    suggested_fix: str

@dataclass
class CodeBlock:
    """Represents a code block extracted from text"""
    chapter_id: str
    index: int
    language: str
    code: str
    start_pos: int
    end_pos: int

class CodeAnalyzer(BaseAnalyzer):
    """Analyzer for code quality validation"""
    
    def get_analyzer_name(self) -> str:
        return "code"
    
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Generate code validation prompt"""
        code_block = context['code_block']
        language = code_block.language
        code = code_block.code
        chapter_context = context.get('chapter_context', '')
        
        prompt = f"""Validate this code snippet:

Language: {language}
Context: From chapter {code_block.chapter_id}
{f"Chapter context: {chapter_context[:500]}" if chapter_context else ""}

Code:
```{language}
{code}
```

Check for:
1. Syntax errors
2. Missing imports or dependencies
3. Undefined variables or functions
4. Logical errors
5. Best practice violations
6. Potential runtime errors

Response format:
{{
    "is_valid": true/false,
    "errors": [
        {{
            "line": line_number_or_null,
            "type": "syntax|import|undefined|logic|style|runtime",
            "description": "오류 설명을 한글로 작성",
            "severity": "error|warning|info",
            "fix": "수정 방법을 한글로 제시"
        }}
    ],
    "overall_quality": "excellent|good|fair|poor",
    "suggestions": ["개선 제안을 한글로 작성"]
}}

IMPORTANT: All 'description', 'fix', and 'suggestions' fields MUST be written in Korean (한글).
"""
        return prompt
    
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze all code blocks in chapters"""
        self.logger.info("Analyzing code quality...")
        
        all_errors = []
        total_code_blocks = 0
        
        for chapter in chapters:
            # Extract code blocks from chapter
            code_blocks = self._extract_code_blocks(chapter)
            total_code_blocks += len(code_blocks)
            
            for code_block in code_blocks:
                # First try static analysis if Python
                if code_block.language.lower() in ['python', 'py']:
                    static_errors = self._static_python_analysis(code_block)
                    all_errors.extend(static_errors)
                
                # Then use LLM for comprehensive analysis
                llm_errors = self._llm_code_analysis(code_block, chapter.text[:1000])
                all_errors.extend(llm_errors)
        
        # Calculate overall code quality score
        error_count = len([e for e in all_errors if e.severity == 'error'])
        warning_count = len([e for e in all_errors if e.severity == 'warning'])
        
        quality_score = max(0.0, 1.0 - (error_count * 0.1 + warning_count * 0.05))
        
        return AnalysisResult(
            analyzer_type="code",
            total_issues=len(all_errors),
            confidence_score=quality_score,
            details=[self._code_error_to_dict(e) for e in all_errors],
            summary=f"Found {error_count} errors and {warning_count} warnings in {total_code_blocks} code blocks"
        )
    
    def _extract_code_blocks(self, chapter: Any) -> List[CodeBlock]:
        """Extract code blocks from chapter text"""
        code_blocks = []
        text = chapter.text
        chapter_id = chapter.get_id()
        
        # Pattern for markdown code blocks
        pattern = r'```(\w*)\n(.*?)```'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for i, match in enumerate(matches):
            language = match.group(1) or 'unknown'
            code = match.group(2)
            
            code_blocks.append(CodeBlock(
                chapter_id=chapter_id,
                index=i,
                language=language,
                code=code.strip(),
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Also look for indented code blocks (4 spaces or tab)
        indented_pattern = r'(?:^|\n)((?:[ ]{4}|\t).*(?:\n(?:[ ]{4}|\t).*)*)'
        indented_matches = re.finditer(indented_pattern, text, re.MULTILINE)
        
        for i, match in enumerate(indented_matches, len(code_blocks)):
            code = match.group(1)
            # Remove indentation
            lines = code.split('\n')
            cleaned_lines = [line[4:] if line.startswith('    ') else line[1:] for line in lines]
            
            code_blocks.append(CodeBlock(
                chapter_id=chapter_id,
                index=i,
                language='unknown',
                code='\n'.join(cleaned_lines).strip(),
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        return code_blocks
    
    def _static_python_analysis(self, code_block: CodeBlock) -> List[CodeError]:
        """Perform static analysis on Python code"""
        errors = []
        
        try:
            # Try to parse as Python AST
            ast.parse(code_block.code)
        except SyntaxError as e:
            errors.append(CodeError(
                chapter_id=code_block.chapter_id,
                code_block_index=code_block.index,
                code_excerpt=code_block.code.split('\n')[e.lineno-1] if e.lineno else code_block.code[:100],
                error_type='syntax',
                line_number=e.lineno,
                description=f"문법 오류: {e.msg}",
                severity='error',
                suggested_fix=f"라인 {e.lineno}의 문법을 확인하세요"
            ))
        
        # Check for common issues
        lines = code_block.code.split('\n')
        
        # Check for missing imports
        used_modules = set()
        imported_modules = set()
        
        for i, line in enumerate(lines):
            # Find imports
            import_match = re.match(r'(?:from\s+(\w+)|import\s+(\w+))', line)
            if import_match:
                module = import_match.group(1) or import_match.group(2)
                imported_modules.add(module)
            
            # Find module usage (simple heuristic)
            for common_module in ['os', 'sys', 'json', 're', 'datetime', 'numpy', 'pandas']:
                if f'{common_module}.' in line and common_module not in imported_modules:
                    used_modules.add(common_module)
        
        for module in used_modules - imported_modules:
            errors.append(CodeError(
                chapter_id=code_block.chapter_id,
                code_block_index=code_block.index,
                code_excerpt=f"Usage of {module}",
                error_type='import',
                line_number=None,
                description=f"'{module}' 모듈이 사용되었지만 import되지 않았습니다",
                severity='error',
                suggested_fix=f"코드 시작 부분에 'import {module}'를 추가하세요"
            ))
        
        return errors
    
    def _llm_code_analysis(self, code_block: CodeBlock, chapter_context: str) -> List[CodeError]:
        """Use LLM for comprehensive code analysis"""
        context = {
            'code_block': code_block,
            'chapter_context': chapter_context
        }
        
        prompt = self.get_prompt(context)
        response_text = self.call_llm(prompt)
        result = self.parse_llm_response(response_text)
        
        errors = []
        for error_data in result.get('errors', []):
            errors.append(CodeError(
                chapter_id=code_block.chapter_id,
                code_block_index=code_block.index,
                code_excerpt=code_block.code.split('\n')[error_data.get('line', 1)-1] if error_data.get('line') else code_block.code[:100],
                error_type=error_data.get('type', 'unknown'),
                line_number=error_data.get('line'),
                description=error_data.get('description', ''),
                severity=error_data.get('severity', 'warning'),
                suggested_fix=error_data.get('fix', '')
            ))
        
        return errors
    
    def _code_error_to_dict(self, error: CodeError) -> Dict[str, Any]:
        """Convert CodeError to dictionary"""
        return {
            "chapter_id": error.chapter_id,
            "code_block_index": error.code_block_index,
            "code_excerpt": error.code_excerpt,
            "error_type": error.error_type,
            "line_number": error.line_number,
            "description": error.description,
            "severity": error.severity,
            "suggested_fix": error.suggested_fix
        } 