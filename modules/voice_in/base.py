"""语音输入模块标准接口（ABC），Phase 2 实现"""

from abc import ABC, abstractmethod
from typing import Callable, Awaitable, Union


class VoiceInBase(ABC):
    """所有语音输入实现必须遵循的接口"""

    @abstractmethod
    async def start_listening(self, on_text: Union[Callable[[str], Awaitable[None]], Callable[[str], None]]) -> None:
        """开始持续监听，检测到语音转文字后调用 on_text 回调（支持同步和异步）"""
        ...

    @abstractmethod
    async def stop_listening(self) -> None:
        """停止监听"""
        ...
