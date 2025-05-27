import asyncio
import os

from openai import AsyncOpenAI, OpenAI

from app.config import Settings
from app.services.llm import LLMService
from langsmith.wrappers import wrap_openai
from langsmith import traceable

API_URL = 'https://api.deepseek.com/v1'

class DeepseekService(LLMService):
    def __init__(self):
        self.api_key = Settings.DEEPSEEK_API_KEY
        self.client = wrap_openai(AsyncOpenAI(api_key=self.api_key,base_url=API_URL))

    def generate(self, prompt: str, **kwargs) -> str:
        # 同步方法调用异步方法
        return asyncio.run(self.agenerate(prompt, **kwargs))

    def get_prompt(self,query:str,**kwargs):
        retrieved_docs = kwargs.get('retrieved_docs')
        intent_type = kwargs.get('intent_type', 'general')  # 获取意图类型，默认为general
        prompt = query
        
        if retrieved_docs:
            context = "\n".join([doc["content"] for doc in retrieved_docs])
            
            # 根据不同意图类型使用不同的prompt模板
            if intent_type == 'technical':
                prompt = f"""
                基于以下技术文档回答问题。请重点关注代码实现细节和技术原理解释：
                
                技术文档：
                {context}
                
                技术问题：
                {query}
                
                请提供详细的技术说明：
                """
            elif intent_type == 'process':
                prompt = f"""
                根据以下文档回答流程相关问题。请重点说明步骤安排和执行顺序：
                
                参考文档：
                {context}
                
                流程问题：
                {query}
                
                请按步骤详细说明：
                """
            elif intent_type == 'interactive':
                prompt = f"""
                基于以下对话上下文回答问题。请注重交互性和用户体验：
                
                对话记录：
                {context}
                
                用户问题：
                {query}
                
                请以对话形式回答：
                """
            elif intent_type == 'analysis':
                prompt = f"""
                根据以下资料进行分析。请重点进行对比和案例分析：
                
                分析材料：
                {context}
                
                分析问题：
                {query}
                
                请进行详细分析：
                """
            else:  # general类型或其他类型
                prompt = f"""
                根据以下上下文回答问题：
                
                上下文：
                {context}
                
                问题：
                {query}
                
                回答：
                """
        return prompt


    @traceable
    async def agenerate(self, prompt: str, **kwargs) -> str:
        print("---------llm is generating response--------")
        # 关于prompt的处理
        prompt = self.get_prompt(query=prompt,**kwargs)
        response = await self.client.chat.completions.create(
            model = 'deepseek-chat',
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=kwargs.get('temperature', 0.5)
        )
        return response.choices[0].message.content

    def stream_generate(self, prompt: str, **kwargs):
        """
        流式生成响应，逐步返回每个 token。
        :param prompt: 用户输入的提示
        :param kwargs: 其他参数（如 temperature）
        """
        print("---------llm is streaming response--------")
        client = wrap_openai(OpenAI(base_url=API_URL,api_key=self.api_key))
        # 关于prompt的处理
        prompt = self.get_prompt(query=prompt,**kwargs)
        stream = client.chat.completions.create(
            model='deepseek-chat',
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get('temperature', 0.5),
            stream=True  # 启用流式输出
        )

        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                print(f"Yielding chunk: {content}")  # 调试日志
                yield content