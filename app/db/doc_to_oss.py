import os

import oss2
from app.config import Settings


class DocToOSS:
    def __init__(self, bucket_name : str = 'rag-java'):
        self.ACCESS_KEY_ID = Settings.ACCESS_KEY_ID
        self.ACCESS_KEY_SECRET = Settings.ACCESS_KEY_SECRET
        self.ENDPOINT_URL = Settings.ENDPOINT_URL
        self.bucket_name = bucket_name


    def get_file(self, file_name):
            auth = oss2.Auth(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET)
            bucket = oss2.Bucket(auth, self.ENDPOINT_URL, self.bucket_name)

            # 设置过期时间
            expiry_seconds = 3600

            return bucket.sign_url('GET', file_name, expiry_seconds)

    def upload_file(self,file_path):
        auth = oss2.Auth(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, self.ENDPOINT_URL, self.bucket_name)
        bucket.put_object_from_file(os.path.basename(file_path), file_path)
        print(f"文件 {file_path} 上传成功")

    def upload_file_to_oss(self, file_stream, filename):
        auth = oss2.Auth(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, self.ENDPOINT_URL, self.bucket_name)

        try:
            if bucket.object_exists(filename):
                return "文件名已存在"

            result = bucket.put_object(filename, file_stream)

            if result.status == 200:
                return None
            else:
                return "文件上传失败"
        except Exception as e:
            return "服务器内部错误"

    def list_files(self):
        auth = oss2.Auth(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, self.ENDPOINT_URL, self.bucket_name)
        files = []
        for obj in oss2.ObjectIterator(bucket):
            files.append(obj.key)
        return files

    def delete_file(self, file_name):
        auth = oss2.Auth(self.ACCESS_KEY_ID, self.ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, self.ENDPOINT_URL, self.bucket_name)

        try:
            if not bucket.object_exists(file_name):
                return "文件不存在"

            bucket.delete_object(file_name)
            return None
        except Exception as e:
            return "服务器内部错误"

if __name__ == '__main__':
    doc_to_oss = DocToOSS()
    url = doc_to_oss.get_file('ComputerArchitecture.pdf')
    print(url)