'''
services/llm/__init__.py
进行抽象接口的定义
'''
# app/services/llm/__init__.py
from abc import ABC, abstractmethod


# from typing import Dict, Any

class LLMService(ABC):
    @abstractmethod
    async def get_prompt(self, query: str, **kwargs):
        pass

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        pass

    async def simple_generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def agenerate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def stream_generate(self, prompt: str, **kwargs) -> str:
        pass
