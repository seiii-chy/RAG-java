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
        prompt = query
        if retrieved_docs:
            context = "\n".join([doc["content"] for doc in retrieved_docs])
            # 关于prompt的处理
            # TODO: 根据实际需求调整prompt的格式
            # blame: HMY 注意这里代码格式的设计，要在几个工厂方法中都完成这样的选择设计
            prompt = f"""
            根据以下检索文档回答问题：
            检索文档：
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