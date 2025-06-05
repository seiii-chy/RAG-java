import json
import time

from flask import current_app

from app.api.dependency import get_llm_service_dependency
from app.utils.tokenizer import Tokenizer
from app.pipelines.tokenizer import ChineseTokenizer


class RAGService:
    def __init__(self, LLMrequire: str = 'deepseek'):
        self.tokenizer = Tokenizer(model_name="BAAI/bge-small-zh-v1.5")
        self.milvus_client = current_app.extensions['milvus']  # 获取 Milvus 客户端
        self.LLMService = LLMrequire
        self.llm_service = get_llm_service_dependency(LLMrequire)  # 初始化 LLM 服务
        self.ChineseTokenizer = ChineseTokenizer()

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

    def hybrid_retrieve(self, query: str, top_k=5, belong_to: int = 0):
        # 1. 文本向量化
        query_vector = self.tokenizer.encode(query)

        # 2. 关键词提取
        query_keyword = self.ChineseTokenizer.extract_keywords_without_weight(query)

        expr = self.build_expression(query_keyword, belong_to)

        # 3. 在 Milvus 中检索
        results = self.milvus_client.hybrid_search(query_vector=query_vector, expr=expr, top_k=top_k)
        print("----------retrieve results:", results)
        # 3. 解析结果
        retrieved_docs = self.fuse_results(results, query_keyword, vector_weight=0.7, keyword_weight=0.3)
        return retrieved_docs

    async def hybrid_search(self, query: str, top_k=5, belong_to: int = 0):
        retrieved_docs = self.hybrid_retrieve(query, top_k=top_k, belong_to=belong_to)

        answer = await self.generate_answer(query, retrieved_docs)

        return {
            "answer": answer,
            "retrieved_docs": retrieved_docs
        }

    def build_expression(self, keywords: list, belong_to: int = 0 ):
        """构建查询表达式"""
        expressions = []

        if keywords:
            keyword_exprs = [f"keywords like '%{kw}%'" for kw in keywords]
            expressions.append(f"({' or '.join(keyword_exprs)})")

        if belong_to == 0:
            expressions.append("belong_to == 0")
        else:
            expressions.append(f"belong_to == {belong_to} or belong_to == 0")  # 包含公共数据
        return " and ".join(expressions) if expressions else ""

    def fuse_results(self, results: list, query_keywords: list, vector_weight: float, keyword_weight: float):
        """融合向量和关键词检索结果"""
        fused = []
        # 第一轮: 处理向量检索结果
        for hits in results:
            for hit in hits:
                entity_fields = hit.fields
                vector_score = hit.score

                content = entity_fields.get("content", "")
                keywords = entity_fields.get("keywords", [])

                # 计算关键词匹配分数
                keyword_score = self.calculate_keyword_score(
                    keywords,
                    query_keywords
                )

                # 计算混合分数
                hybrid_score = (vector_weight * vector_score +
                                keyword_weight * keyword_score)

                # 构建结果对象
                result = {
                    "id": hit.get("id"),
                    "content": content,
                    "file_name": entity_fields.get("file_name"),
                    "belong_to": entity_fields.get("belong_to"),
                    "vector_score": vector_score,
                    "keyword_score": keyword_score,
                    "hybrid_score": hybrid_score,
                    "matched_keywords": list(set(query_keywords) &
                                             set(keywords.split(',')))
                }
                fused.append(result)

        return fused

    def calculate_keyword_score(self,doc_keywords: str, query_keywords: list) -> float:
        """计算关键词匹配分数"""
        if not doc_keywords or not query_keywords:
            return 0.0

        doc_kw_list = doc_keywords.split(',')
        matched_count = len(set(query_keywords) & set(doc_kw_list))
        return matched_count / len(query_keywords)

    async def stream_output(self, query: str, top_k=5, user_id: int = 0):
        # 1. 检索相关文档
        retrieved_docs = self.hybrid_retrieve(query, top_k=top_k, belong_to=user_id)
        # 2. 返回文档
        doc_payload = {
            "type": "docs",
            "data": [
                {
                    "id": doc.get("id"),
                    "title": doc.get("file_name"),
                    "content": doc.get("content"),
                    "score": doc.get("hybrid_score"),
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
