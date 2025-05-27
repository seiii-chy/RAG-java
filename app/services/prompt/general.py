from app.services.prompt.template import PromptTemplate

# 通用类意图prompt模板
class GeneralPrompt(PromptTemplate):
    def generate(self, query: str, context: str = None) -> str:
        if not context:
            return query
        return f"""
        根据以下上下文回答问题：
        
        上下文：
        {context}
        
        问题：
        {query}
        
        回答：
        """