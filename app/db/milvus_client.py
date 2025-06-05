from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility

from app.config import Settings


class MilvusClient:
    def __init__(self, port: str = '19530',app=None,collection_name = "java_interview_qa",dim=384):
        self.host = Settings.MILVUS_HOST # Milvus 服务器地址
        self.port = port  # Milvus 服务器端口
        self.db_name = 'Java_knowledge_base'
        self.token = Settings.MILVUS_TOKEN
        self.uri = Settings.MILVUS_URL
        self.collection_name = collection_name  # 默认集合名称
        self.dim = dim  # 与嵌入模型维度匹配
        self.app = app
        if app is not None:
            self.connect(app)

    def connect(self,_app):
        """连接到 Milvus 服务器"""
        try:
            # NOT USING LAN CONNECT
            # connections.connect(alias="default",host=self.host, port=self.port, db_name=self.db_name)
            connections.connect(uri=self.uri, token=self.token)
            self.collection = Collection(self.collection_name)
            self.collection.load()
            print(f"ℹ️ Milvus连接成功")
            _app.extensions['milvus'] = self  # 存入扩展系统
            # print(f"Connected to Milvus at {self.host}:{self.port}:{self.db_name}")
        except Exception as e:
            print(f"Failed to connect to Milvus: {e}")


    def close(self):
        """关闭连接"""
        connections.disconnect("default")
        print("ℹ️ Milvus连接已关闭")

    def search(self, query_vector, top_k=5):
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        print(f"query_vector embedding done")
        results = self.collection.search(
            data=[query_vector],
            anns_field="chunk_embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content","file_name"],
        )
        return results

    def hybrid_search(self,query_vector, expr, top_k=5):
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[query_vector],
            anns_field="chunk_embedding",
            param=search_params,
            limit=top_k,
            output_fields=["content","keywords","file_name", "belong_to"],
            expr=expr
        )
        return results

    def change_collection(self, collection_name):
        """切换集合"""
        if utility.has_collection(collection_name):
            self.collection_name = collection_name
            self.collection = Collection(self.collection_name)
            self.collection.load()
            print(f"ℹ️ 切换到集合 {self.collection_name} 成功")
        else:
            print(f"❗集合 {collection_name} 不存在")

    def delete_by_file_name(self, file_name: str):
        """根据文件名删除数据"""
        if not utility.has_collection(self.collection_name):
            print(f"❗集合 {self.collection_name} 不存在")
            return
        expr = f"file_name == '{file_name}'"
        self.collection.delete(expr)
        self.collection.flush()
        print(f"ℹ️ 已删除文件名为 {file_name} 的数据")

