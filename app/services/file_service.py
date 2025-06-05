from flask import jsonify, current_app
import os
import unicodedata
import re
from app.models.file import File
from app.extensions import db

MAX_FILE_SIZE = 50 * 1024 * 1024 # 单个文件最大20MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'md'} # 允许的文件类型


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def safe_filename(filename: str) -> str:
    """
    安全处理文件名（保留中文）
    """
    # 1. Unicode标准化
    normalized = unicodedata.normalize('NFKC', filename)

    # 2. 过滤危险字符（保留中文、字母、数字、下划线、短横线、点号、空格）
    cleaned = re.sub(r'[^\w\u4e00-\u9fff\s\-_.]', '', normalized)

    # 3. 替换路径分隔符
    cleaned = cleaned.replace('/', '_').replace('\\', '_')

    # 4. 处理连续空格和短横线
    cleaned = re.sub(r'[\-\s]+', '-', cleaned.strip())

    # 5. 长度限制（保留最后255字符）
    return cleaned[:255]

def store_file(files, user_id=0, file_category=None):
    doc_to_oss = current_app.extensions['oss']
    processed_pipeline = current_app.extensions['pipeline']
    saved_files = []
    for file in files:
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file'}), 400

        # 验证文件大小
        file.seek(0, os.SEEK_END)
        file_siem = file.tell()
        file.seek(0)
        if file_siem > MAX_FILE_SIZE:
            return jsonify({'error': 'File too big'}), 400
        print(file.filename)
        file_name = safe_filename(file.filename)
        print(file_name)
        error = doc_to_oss.upload_file_to_oss(file.stream, file_name)
        if error:
            return jsonify({'error': error}), 400

        saved_files.append(file_name)
        # 处理文件
        file.seek(0)
        processed_pipeline.process_document(file.stream, file_name, user_id)
        # 保存文件信息到数据库
        new_file = File(name=file_name, category=file_category, collection_name=current_app.extensions['milvus'].collection_name)
        db.session.add(new_file)
        db.session.commit()

    return jsonify({'success': True, 'saved_files': saved_files}), 200


def get_files(file_category):
    files = File.query.filter(File.category == file_category).all()
    file_lists = [{"file_name": file.name} for file in files]
    return file_lists