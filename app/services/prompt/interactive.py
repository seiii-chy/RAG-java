from app.services.prompt.template import PromptTemplate
from app.models.conversation import Conversation

# 交互类意图prompt模板
class InteractivePrompt(PromptTemplate):
    def generate(self, query: str, context: str = None, **kwargs) -> str:
        conversation_id = kwargs.get('conversation_id')
        conversation_history = None
        if conversation_id:
            conversation = Conversation.query.get(conversation_id)
            conversation_history = conversation.messages

        history_str = ""
        if conversation_history:
            # 取最近6条消息
            recent_history = conversation_history[-6:]
            formatted_history = []
            for msg in recent_history:
                formatted_history.append(f"{msg.role}: {msg.content}")
            history_str = "\n".join(formatted_history)
            history_str = f"\n以下是最近的对话历史：\n{history_str}\n"

        if not context:
            return f"""
            你是一个技术专家，现在是用户在咨询一个技术难点时候想要进行多轮交互（如多轮对话、反馈、追问等），用户想要进一步了解技术点或者对刚才的回答做出质疑之类的反馈，你需要回答用户的问题，请遵循以下规则：
            
            1. 保证上下文正确感知，也就是说需要识别指代关系，具体表现在用户是想要对哪个方面的内容进行的深层交互
            2. 保证内容的反思性，用户可能会对刚才的回答提出质疑，你需要对刚才的回答进行反思，根据我们查询到的客观权威知识分析是否存在问题，不能允许以及生成主观甚至错误的内容
            3. 保证渐进式引导，通过追问细化用户的需求，一步步引导用户深入到技术点的核心，避免一次性给出过多信息导致用户无法消化

            回答结构：

            第一段：分析用户提出的问题的意图（是要深入了解知识，还是发出质疑等），根据上下文明确我们回答的内容的方向
            第二段：根据用户的需求反思刚才的回答，通过客观知识分析是否存在对应的问题，如果没问题要基于正确事实向用户确认答案的正确并以客观知识回复用户的疑惑点，有问题要敢于承认并且进行纠正，提出错误的内容后讲解正确的内容，结合正确的内容重新给出用户需求的客观正确的回答
            第三段：对用户提出的问题进行追问，细化用户的需求，逐步引导用户深入到技术点的核心，避免一次性给出过多信息导致用户无法消化
            
            这是对话历史上下文信息：
            {history_str}
            
            这是需要回答的技术问题：
            {query}
            
            请按照已经定义的规则和结构进行回答。
            """

        return f"""
        你是一个技术专家，现在是用户在咨询一个技术难点时候想要进行多轮交互（如多轮对话、反馈、追问等），用户想要进一步了解技术点或者对刚才的回答做出质疑之类的反馈，你需要回答用户的问题，请遵循以下规则：
        
        1. 保证上下文正确感知，也就是说需要识别指代关系，具体表现在用户是想要对哪个方面的内容进行的深层交互
        2. 保证内容的反思性，用户可能会对刚才的回答提出质疑，你需要对刚才的回答进行反思，根据我们查询到的客观权威知识分析是否存在问题，不能允许以及生成主观甚至错误的内容
        3. 保证渐进式引导，通过追问细化用户的需求，一步步引导用户深入到技术点的核心，避免一次性给出过多信息导致用户无法消化

        回答结构：

        第一段：分析用户提出的问题的意图（是要深入了解知识，还是发出质疑等），根据上下文明确我们回答的内容的方向
        第二段：根据用户的需求反思刚才的回答，通过客观知识分析是否存在对应的问题，如果没问题要基于正确事实向用户确认答案的正确并以客观知识回复用户的疑惑点，有问题要敢于承认并且进行纠正，提出错误的内容后讲解正确的内容，结合正确的内容重新给出用户需求的客观正确的回答
        第三段：对用户提出的问题进行追问，细化用户的需求，逐步引导用户深入到技术点的核心，避免一次性给出过多信息导致用户无法消化
        
        这是提供的技术文档：
        {context}
        
        这是对话历史上下文信息：
        {history_str}
        
        这是需要回答的技术问题：
        {query}
        
        请按照已经定义的规则和结构进行回答。
        """