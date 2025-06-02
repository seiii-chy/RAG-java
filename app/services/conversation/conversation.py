from app.models.conversation import Conversation
from app.extensions import db

class ConversationService:
    @staticmethod
    def get_conversations(user_id):
        conversations = Conversation.query.filter(Conversation.user_id == user_id).all()
        if not conversations:
            return None
        conversation_lists = [{"id" : conv.id, "title": conv.title} for conv in conversations]
        return conversation_lists

    @staticmethod
    def get_conversation(conversation_id):
        conversation = Conversation.query.get(conversation_id)
        return conversation

    @staticmethod
    async def create_conversation(user_id, content):
        from app.services.llm.factory import get_llm_service
        llm_service = get_llm_service('deepseek')
        prompt = f"""
        根据以下上下文和限制生成一个对话标题：
        上下文：
        {content}
        限制：
        1. 标题应简洁明了，能够概括对话的主题。
        2. 标题应避免使用模糊或通用的词语。
        3. 只生成一个标题，不需要其他内容。
        回答：
        """
        title = await llm_service.simple_generate(prompt)

        new_conversation = Conversation(user_id=user_id, title=title)
        db.session.add(new_conversation)
        db.session.commit()
        new_conversation.add_message(role='user', content=content)
        return new_conversation.id

    @staticmethod
    def add_conversation_message(conversation_id, role, content):
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return None
        msg = conversation.add_message(role, content)
        db.session.commit()
        return msg.id

    @staticmethod
    def delete_conversation(conversation_id):
        conversation = Conversation.query.get(conversation_id)
        if not conversation:
            return False
        db.session.delete(conversation)
        db.session.commit()
        return True