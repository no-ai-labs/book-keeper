"""
Base Analyzer Abstract Class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json
import logging

@dataclass
class AnalysisResult:
    """Base result class for all analyzers"""
    analyzer_type: str
    total_issues: int
    confidence_score: float
    details: List[Dict[str, Any]]
    summary: str

class BaseAnalyzer(ABC):
    """Base class for all document analyzers"""
    
    def __init__(self, model_type: str = "claude", logger: Optional[logging.Logger] = None):
        self.model_type = model_type
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.llm_client = self._create_llm_client(model_type)
    
    def _create_llm_client(self, model_type: str):
        """Create LLM client based on model type"""
        if model_type == "claude":
            from anthropic import Anthropic
            import os
            return Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        elif model_type in ["openai", "gpt"]:
            from openai import OpenAI
            import os
            return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
    
    @abstractmethod
    def get_analyzer_name(self) -> str:
        """Return the name of this analyzer"""
        pass
    
    @abstractmethod
    def analyze(self, chapters: List[Any]) -> AnalysisResult:
        """Analyze the given chapters and return results"""
        pass
    
    @abstractmethod
    def get_prompt(self, context: Dict[str, Any]) -> str:
        """Get the analysis prompt in English"""
        pass
    
    def parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response, handling both direct JSON and code-wrapped JSON"""
        try:
            # Try direct JSON parsing first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Handle Claude's code block wrapping
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    json_str = response_text[json_start:json_end].strip()
                    return json.loads(json_str)
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    json_str = response_text[json_start:json_end].strip()
                    return json.loads(json_str)
            raise
    
    def call_llm(self, prompt: str) -> str:
        """Call the LLM with the given prompt"""
        try:
            if self.model_type == "claude":
                response = self.llm_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4000,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                return response.content[0].text
            else:  # OpenAI
                response = self.llm_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a technical documentation analyzer. Provide detailed analysis in the requested JSON format."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error calling LLM: {e}")
            raise 