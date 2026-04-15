"""Agent 模块标准接口（ABC），后期可替换实现"""

from abc import ABC, abstractmethod


class AgentBase(ABC):
    """所有 Agent 实现必须遵循的接口"""

    @abstractmethod
    async def chat(self, text: str) -> str:
        """接收文字输入，返回文字回复"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放资源"""
        ...
