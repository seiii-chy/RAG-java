import asyncio

from openai import AsyncOpenAI, OpenAI

from app.config import Settings
from app.services.llm import LLMService
from langsmith.wrappers import wrap_openai
from langsmith import traceable

from app.services.intent_classifier import IntentClassificationService
from app.services.prompt.factory import get_prompt_template

API_URL = 'https://api.deepseek.com/v1'


class DeepseekService(LLMService):
    def __init__(self):
        self.api_key = Settings.DEEPSEEK_API_KEY
        self.client = wrap_openai(AsyncOpenAI(api_key=self.api_key, base_url=API_URL))

    def generate(self, prompt: str, **kwargs) -> str:
        # 同步方法调用异步方法
        return asyncio.run(self.agenerate(prompt, **kwargs))

    async def get_prompt(self, query: str, **kwargs):
        # 获取检索文档
        retrieved_docs = kwargs.get('retrieved_docs')

        context = "\n".join([doc["content"] for doc in retrieved_docs]) if retrieved_docs else None

        # 获取意图分类结果
        intent_classifier = IntentClassificationService()
        intent = await intent_classifier.classify_intent(query)

        # 根据意图类型获取对应的prompt模板并生成prompt
        prompt_template = get_prompt_template(intent.value)
        generated_prompt = prompt_template.generate(query, context if context else "")
        return str(generated_prompt)

    @traceable
    async def agenerate(self, prompt: str, **kwargs) -> str:
        print("---------llm is generating response--------")
        # 关于prompt的处理
        prompt = await self.get_prompt(query=prompt, **kwargs)
        response = await self.client.chat.completions.create(
            model='deepseek-chat',
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=kwargs.get('temperature', 0.5)
        )
        return response.choices[0].message.content

    async def stream_generate(self, prompt: str, **kwargs):
        """
        流式生成响应，逐步返回每个 token。
        :param prompt: 用户输入的提示
        :param kwargs: 其他参数（如 temperature）
        """
        print("---------llm is streaming response--------")
        client = wrap_openai(OpenAI(base_url=API_URL, api_key=self.api_key))
        # 关于prompt的处理
        prompt = await self.get_prompt(query=prompt, **kwargs)
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
