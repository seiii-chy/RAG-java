from typing import Dict
from app.services.prompt.template import PromptTemplate
from app.services.prompt.technical import TechnicalPrompt
from app.services.prompt.process import ProcessPrompt
from app.services.prompt.interactive import InteractivePrompt
from app.services.prompt.analysis import AnalysisPrompt
from app.services.prompt.general import GeneralPrompt

PROMPT_TEMPLATES = {
    'technical': TechnicalPrompt,
    'process': ProcessPrompt,
    'interactive': InteractivePrompt,
    'analysis': AnalysisPrompt,
    'general': GeneralPrompt
}

class PromptFactory:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._templates = {}
            cls._instance._init_templates()
        return cls._instance
    
    def _init_templates(self):
        for name, template_class in PROMPT_TEMPLATES.items():
            self._templates[name] = template_class("")
    
    def get_prompt_template(self, intent_type: str = 'general') -> PromptTemplate:
        if intent_type not in self._templates:
            raise ValueError(f"Invalid prompt template type: {intent_type}")
        return self._templates[intent_type]
    
    def register_template(self, name: str, template_class: type):
        """注册新的模板类型"""
        if not issubclass(template_class, PromptTemplate):
            raise TypeError("Template class must inherit from PromptTemplate")
        self._templates[name] = template_class("")
        PROMPT_TEMPLATES[name] = template_class