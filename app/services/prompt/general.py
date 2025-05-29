from app.services.prompt.template import PromptTemplate

# 通用类意图prompt模板
class GeneralPrompt(PromptTemplate):
    def generate(self, query: str, context: str = None) -> str:
        if not context:
            return query
        return f"""
        根据提供的技术文档回答问题：
        
        技术文档：
        {context}
        
        问题：
        {query}
        
        回答：
        """