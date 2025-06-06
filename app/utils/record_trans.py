# -*- coding: utf8 -*-
import json
import os
import tempfile
import time
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from app.config import Settings


accessKeyId = Settings.Aliyun_AK_ID
accessKeySecret = Settings.Aliyun_AK_SECRET
appKey = Settings.Aliyun_APP_KEY


class Transvoice:

    def __init__(self):
        pass

    def fileTrans(fileLink:str):
        # 地域ID，固定值。
        REGION_ID = "cn-shanghai"
        PRODUCT = "nls-filetrans"
        DOMAIN = "filetrans.cn-shanghai.aliyuncs.com"
        API_VERSION = "2018-08-17"
        POST_REQUEST_ACTION = "SubmitTask"
        GET_REQUEST_ACTION = "GetTaskResult"
        # 请求参数
        KEY_APP_KEY = "appkey"
        KEY_FILE_LINK = "file_link"
        KEY_VERSION = "version"
        KEY_ENABLE_WORDS = "enable_words"
        # 是否开启智能分轨
        KEY_AUTO_SPLIT = "auto_split"
        # 响应参数
        KEY_TASK = "Task"
        KEY_TASK_ID = "TaskId"
        KEY_STATUS_TEXT = "StatusText"
        KEY_RESULT = "Result"
        # 状态值
        STATUS_SUCCESS = "SUCCESS"
        STATUS_RUNNING = "RUNNING"
        STATUS_QUEUEING = "QUEUEING"


        client = AcsClient(accessKeyId, accessKeySecret, REGION_ID)
        # 提交录音文件识别请求
        postRequest = CommonRequest()
        postRequest.set_domain(DOMAIN)
        postRequest.set_version(API_VERSION)
        postRequest.set_product(PRODUCT)
        postRequest.set_action_name(POST_REQUEST_ACTION)
        postRequest.set_method('POST')
        # 新接入请使用4.0版本，已接入（默认2.0）如需维持现状，请注释掉该参数设置。
        # 设置是否输出词信息，默认为false，开启时需要设置version为4.0。
        task = {KEY_APP_KEY: appKey, KEY_FILE_LINK: fileLink, KEY_VERSION: "4.0", KEY_ENABLE_WORDS: False}
        # 开启智能分轨，如果开启智能分轨，task中设置KEY_AUTO_SPLIT为True。
        # task = {KEY_APP_KEY : appKey, KEY_FILE_LINK : fileLink, KEY_VERSION : "4.0", KEY_ENABLE_WORDS : False, KEY_AUTO_SPLIT : True}
        task = json.dumps(task)
        postRequest.add_body_params(KEY_TASK, task)
        taskId = ""
        try:
            postResponse = client.do_action_with_exception(postRequest)
            postResponse = json.loads(postResponse)
            print(postResponse)
            statusText = postResponse[KEY_STATUS_TEXT]
            if statusText == STATUS_SUCCESS:
                print("录音文件识别请求成功响应！")
                taskId = postResponse[KEY_TASK_ID]
            else:
                print("录音文件识别请求失败！")
                return
        except ServerException as e:
            print(e)
        except ClientException as e:
            print(e)
        # 创建CommonRequest，设置任务ID。
        getRequest = CommonRequest()
        getRequest.set_domain(DOMAIN)
        getRequest.set_version(API_VERSION)
        getRequest.set_product(PRODUCT)
        getRequest.set_action_name(GET_REQUEST_ACTION)
        getRequest.set_method('GET')
        getRequest.add_query_param(KEY_TASK_ID, taskId)
        # 提交录音文件识别结果查询请求
        # 以轮询的方式进行识别结果的查询，直到服务端返回的状态描述符为"SUCCESS"、"SUCCESS_WITH_NO_VALID_FRAGMENT"，
        # 或者为错误描述，则结束轮询。
        while True:
            try:
                getResponse = client.do_action_with_exception(getRequest)
                getResponse = json.loads(getResponse)
                print(getResponse)
                statusText = getResponse[KEY_STATUS_TEXT]
                if statusText == STATUS_RUNNING or statusText == STATUS_QUEUEING:
                    # 继续轮询
                    time.sleep(10)
                else:
                    # 退出轮询
                    break
            except ServerException as e:
                print(e)
            except ClientException as e:
                print(e)
        if statusText == STATUS_SUCCESS:
            print("录音文件识别成功！")
        else:
            print("录音文件识别失败！")
        text = getResponse[KEY_RESULT]
        return text

ALLOWED_EXTENSIONS = {'wav', 'pcm', 'mp3'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_temp_file(file):
    """安全保存临时文件（自动关闭句柄）"""
    try:
        _, ext = os.path.splitext(file.filename)
        fd, path = tempfile.mkstemp(suffix=ext)
        with os.fdopen(fd, 'wb') as tmp:
            file.save(tmp)
        return path
    except Exception as e:
        if 'path' in locals() and os.path.exists(path):
            os.unlink(path)
        raise



if __name__ == "__main__":
    fileLink = "https://gw.alipayobjects.com/os/bmw-prod/0574ee2e-f494-45a5-820f-63aee583045a.wav"
    Transvoice.fileTrans(fileLink=fileLink)

