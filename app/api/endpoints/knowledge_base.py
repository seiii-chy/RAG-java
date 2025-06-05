from flask import Blueprint, request, jsonify, g, current_app

from app.models.file import File
from app.utils.tokenUtils import token_required
from app.services.file_service import store_file, get_files
from app.extensions import oss_client, db

bp = Blueprint('knowledge_base', __name__, url_prefix='/knowledge_base')

@bp.route('/upload_file', methods=['POST'])
@token_required
async def upload_file():
    user = g.user
    if user.user_type != 'Administrator':
        return jsonify({'error': 'You are not authorized'}), 401

    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('files')
    collection_name = request.form.get('collection_name', 'java_doc_plus')
    category = request.form.get('category', 'Java开发')
    milvus_client = current_app.extensions['milvus']
    if milvus_client.collection_name != collection_name:
        milvus_client.change_collection(collection_name)
    return store_file(files, user.id, category)

@bp.route('/list_files', methods=['GET'])
@token_required
async def list_files():
    # 获取文件列表
    files = oss_client.list_files()
    # 返回文件列表
    return {"files": files}, 200


@bp.route('/get_file/<category>', methods=['GET'])
@token_required
async def get_file(category):
    files = get_files(category)

    return {"files": files}, 200

@bp.route('send_file', methods=['POST'])
async def send_file():
    data = request.get_json()
    file_name = data.get('file_name')
    category = data.get('category', 'Java开发')
    new_file = File(name=file_name, category=category)
    db.session.add(new_file)
    db.session.commit()

    return jsonify({'msg': 'File uploaded successfully', 'id': new_file.id}), 200






