'''
basic chat endpoint
'''
import logging
import os

from flask import request, jsonify, Blueprint

from app.api.dependency import get_llm_service_dependency
from app.db.voice_to_oss import Voice_to_oss
from app.utils.intent_classifier_bert import IntentClassificationService
from app.utils.record_trans import Transvoice, save_temp_file, allowed_file

bp = Blueprint('chat', __name__)



@bp.route('/chat', methods=['POST'])
async def chat():
    provider = request.args.get('provider', 'deepseek')
    prompt = request.json['prompt']

    service = get_llm_service_dependency(provider)

    result = await service.agenerate(prompt)

    return jsonify({'result': result,
                    'provider': provider})

@bp.route('/classify', methods=['POST'])
async def classify():
    import app.utils.intent_classifier_bert
    text = request.args.get('text', 'no text')

    service = IntentClassificationService()

    result = await service.classify_intent(text)
    print(result)

    return jsonify({'result': result.value})

@bp.route('/voice_to_text',methods = ['POST'])
def speech_to_text():
    object_key = None
    # 校验音频文件
    if 'audio' not in request.files:
        return jsonify({'error': '未检测到音频文件'}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({'error': '无效文件'}), 400
    if not allowed_file(audio_file.filename):
        return jsonify({'error': '不支持的文件格式'}), 400

    # 保存临时文件
    temp_path = save_temp_file(audio_file)

    try:
        voice_to_oss = Voice_to_oss()
        object_key, oss_url = voice_to_oss.upload_file(temp_path)
        result_text = Transvoice.fileTrans(fileLink=oss_url)  # 阿里云方案
        # result_text = recognize_local(temp_path)  # 本地方案

        if not result_text:
            return jsonify({'error': '识别失败'}), 500

        return jsonify({'text': result_text})

    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500
    finally:
        try:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)  # 比remove更安全的删除方式
        except Exception as e:
            logging.warning(f"临时文件清理失败: {str(e)}")

        try:
            if object_key:
                Voice_to_oss().cleanup_file(object_key)
        except Exception as e:
            logging.warning(f"OSS清理失败: {str(e)}")

