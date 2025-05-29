import json
import time

from flask import current_app

from app.api.dependency import get_llm_service_dependency
from app.utils.tokenizer import Tokenizer

from app.services.intent_classifier import IntentClassificationService


class RAGService:
    def __init__(self, LLMrequire: str = 'deepseek'):
        self.tokenizer = Tokenizer(model_name="BAAI/bge-small-zh-v1.5")
        self.milvus_client = current_app.extensions['milvus']  # 获取 Milvus 客户端
        self.LLMService = LLMrequire
        self.llm_service = get_llm_service_dependency(LLMrequire)  # 初始化 LLM 服务

    def retrieve(self, query: str, top_k=5):
        print("--------------encoding------------")
        # 1. 文本向量化
        query_vector = self.tokenizer.encode(query)

        # 2. 在 Milvus 中检索
        results = self.milvus_client.search(query_vector=query_vector, top_k=top_k)
        print("----------retrieve files done------------------")
        # 3. 解析结果
        retrieved_docs = []
        for hit in results[0]:
            retrieved_docs.append({
                "id": hit.id,
                "score": hit.score,
                "content": hit.get("content"),
                "name": hit.get("file_name"),
            })
        return retrieved_docs

    async def generate_answer(self, query: str, retrieved_docs: list):
        # # 1. 构造提示
        # prompt = await self.llm_service.get_prompt(query, retrieved_docs=retrieved_docs)

        # 2. 使用 LLM 生成答案
        answer = await self.llm_service.agenerate(query, retrieved_docs=retrieved_docs)
        print("answer: ", answer)
        return answer

    async def query(self, query: str, top_k=5):
        # 1. 意图识别
        # intent_classifier = IntentClassificationService()
        # intent = await intent_classifier.classify_intent(query)
        # print("----------intent classify done------------------", intent.value)

        # 2. 检索相关文档
        retrieved_docs = self.retrieve(query, top_k=top_k)
        print("Yes" if retrieved_docs else "No")  # 调试日志
        # print("----------retrieve docs done------------------")

        # 3. 生成答案
        answer = await self.generate_answer(query, retrieved_docs)
        print("yes" if answer else "no")  # 调试日志
        # ("----------generate answer done------------------")

        return {
            "answer": answer,
            "retrieved_docs": retrieved_docs
            # "intent": intent.value
        }

    def hybrid_retrieve(self, query: str, top_k=5, keywords: list = None):
        # 1. 文本向量化
        query_vector = self.tokenizer.encode(query)

        # 2. 在 Milvus 中检索
        results = self.milvus_client.search(query_vector=query_vector, top_k=top_k)
        print("----------retrieve results:", results)
        # 3. 解析结果
        retrieved_docs = []
        for hit in results[0]:
            retrieved_docs.append({
                "id": hit.id,
                "score": hit.score,
                "content": hit.get("content"),
                "name": hit.get("file_name"),
            })
        return retrieved_docs

    async def hybrid_search(self, query: str, top_k=5, keywords: list = None):
        pass

    async def stream_output(self, query: str, top_k=5):
        # 1. 检索相关文档
        retrieved_docs = self.retrieve(query, top_k=top_k)
        # 2. 返回文档
        doc_payload = {
            "type": "docs",
            "data": [
                {
                    "id": doc.get("id"),
                    "title": doc.get("name"),
                    "content": doc.get("content"),
                    "score": doc.get("score"),
                }
                for doc in retrieved_docs
            ]
        }
        yield json.dumps(doc_payload)

        # 3. 流式生成内容
        async for chunk in self.llm_service.stream_generate(
                prompt=query,
                retrieved_docs=retrieved_docs
        ):
            # 内容数据包
            content_payload = {
                "type": "content",
                "data": chunk,
                "timestamp": time.time()
            }
            yield json.dumps(content_payload)
