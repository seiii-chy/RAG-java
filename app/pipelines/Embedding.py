from typing import List, Dict

from sentence_transformers import SentenceTransformer
from pymilvus import connections,  Collection, utility, MilvusException

from app.models.document import DocumentModel


# 1. 初始化Embedding模型
class EmbeddingGenerator:
    def __init__(self, model_name='BAAI/bge-small-zh-v1.5',device='cpu'):
        self.model = SentenceTransformer(model_name)
        self.dim = 512  # 嵌入向量维度
        self.device = device

    def generate(self, texts):
        """批量生成嵌入向量"""
        return self.model.encode(texts, convert_to_tensor=False, device=self.device)


# 2. Milvus向量数据库操作类
class VectorDB:
    def __init__(self, milvus_uri, token,dim=512):
        self.milvus_uri = milvus_uri
        self.token = token
        self.collection_name = "java_doc_plus"
        self.dim = dim

        # 连接Milvus
        connections.connect(uri=self.milvus_uri, token=self.token)

        # 如果集合不存在则创建
        if not utility.has_collection(self.collection_name):
            self._create_collection()

        self.collection = Collection(self.collection_name)

    def _create_collection(self):
        """创建带索引的集合"""
        try:
            # 检查集合是否已存在
            if not utility.has_collection(self.collection_name):
                # 创建集合
                schema = DocumentModel.create_schema()
                collection = Collection(
                    name=self.collection_name,
                    schema=schema,
                )

                # 创建向量索引
                index_params = {
                    "index_type": "IVF_FLAT",
                    "metric_type": "L2",
                    "params": {"nlist": 128}
                }
                collection.create_index(
                    field_name="chunk_embedding",
                    index_params=index_params
                )
                print(f"集合 {self.collection_name} 创建成功")
            else:
                print(f"集合 {self.collection_name} 已存在")
        except MilvusException as e:
            print(f"创建集合失败: {e}")

    def add_documents(self, documents: List[Dict]):
        data = []
        for doc in documents:
            entity = {
                "content": doc["raw_text"],
                "file_name": doc["file_name"],
                "chunk_index": doc["chunk_index"],
                "keywords": ",".join([kw[0] for kw in doc["keywords"]]),  # 将列表转为字符串
                "chunk_embedding": doc["chunk_vector"],
                # "summary_embedding": doc["summary_vector"],
                # "summary": doc["summary"],
                "belong_to": doc["user_id"]
            }
            data.append(entity)

        # 批量插入
        self.collection.insert(data)
        self.collection.flush()


# 3. 使用示例
if __name__ == "__main__":
    print("hello")
