from flask import jsonify, Blueprint, request, g

from app.utils.tokenUtils import token_required

from app.services.conversation.conversation import ConversationService

bp = Blueprint('conversation', __name__, url_prefix='/conversation')



@bp.route('/getConversations', methods=['GET'])
@token_required
async def get_conversations():
    """
    获取用户的所有对话
    """
    user = g.user
    user_id = user.id
    conversation_lists = ConversationService.get_conversations(user_id)
    if not conversation_lists:
        return jsonify({"error": "No conversations found"}), 404

    return jsonify({"conversations": conversation_lists}), 200

@bp.route('/get/<int:conversation_id>', methods=['GET'])
async  def get_conversation(conversation_id):
    """
    获取指定对话的详细信息
    """
    conversation = ConversationService.get_conversation(conversation_id)
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

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    conversation_id = await ConversationService.create_conversation(user_id, content)

    return jsonify({"message": "Conversation created successfully", "conversation_id": conversation_id}), 200

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

    msg_id = ConversationService.add_conversation_message(conversation_id, role, content)
    if not msg_id:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify({"message": "Message added successfully", "message_id": msg_id}), 200


@bp.route('/delete/<int:conversation_id>', methods=['DELETE'])
async def delete_conversation(conversation_id):
    """
    删除指定对话
    """
    success = ConversationService.delete_conversation(conversation_id)
    if not success:
        return jsonify({"error": "Conversation not found"}), 404

    return jsonify({"message": "Conversation deleted successfully"}), 200