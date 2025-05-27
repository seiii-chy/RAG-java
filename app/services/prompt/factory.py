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

def get_prompt_template(intent_type: str = 'general') -> PromptTemplate:
    if intent_type not in PROMPT_TEMPLATES:
        raise ValueError(f"Invalid prompt template type: {intent_type}")
    return PROMPT_TEMPLATES[intent_type]