from flask import jsonify, Blueprint, request, g

from app.utils.tokenUtils import token_required
from app.models.conversation import Conversation
from app.api.dependency import get_llm_service_dependency
from app.extensions import db

bp = Blueprint('conversation', __name__, url_prefix='/conversation')



@bp.route('/getConversations', methods=['GET'])
@token_required
async def get_conversations():
    """
    获取用户的所有对话
    """
    user = g.user
    user_id = user.id
    conversations = Conversation.query.filter(Conversation.user_id == user_id).all()
    if not conversations:
        return jsonify({"error": "No conversations found"}), 404

    conversation_lists = [{"id" : conv.id, "title": conv.title} for conv in conversations]

    return jsonify({"conversations": conversation_lists}), 200

@bp.route('/get/<int:conversation_id>', methods=['GET'])
async  def get_conversation(conversation_id):
    """
    获取指定对话的详细信息
    """
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify( conversation.to_dict() ), 200

@bp.route('/create', methods=['POST'])
async def create_conversation():
    """
    创建新的对话
    """
    data = request.get_json()
    user_id = data.get('user_id')
    content = data.get('content')

    llm_service = get_llm_service_dependency('deepseek')
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

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    new_conversation = Conversation(user_id=user_id, title=title)
    db.session.add(new_conversation)
    db.session.commit()
    new_conversation.add_message(role='user', content=content)

    return jsonify({"message": "Conversation created successfully", "conversation_id": new_conversation.id}), 200

@bp.route('/add_message/<int:conversation_id>', methods=['POST'])
async def add_conversation_message(conversation_id):
    """
    向指定对话添加消息
    """
    data = request.get_json()
    role = data.get('role')
    content = data.get('content')

    if not role or not content:
        return jsonify({"error": "Role and content are required"}), 400

    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    msg= conversation.add_message(role, content)
    db.session.commit()

    return jsonify({"message": "Message added successfully", "message_id": msg.id}), 200


@bp.route('/delete/<int:conversation_id>', methods=['DELETE'])
async def delete_conversation(conversation_id):
    """
    删除指定对话
    """
    conversation = Conversation.query.get(conversation_id)
    if not conversation:
        return jsonify({"error": "Conversation not found"}), 404

    db.session.delete(conversation)
    db.session.commit()

    return jsonify({"message": "Conversation deleted successfully"}), 200