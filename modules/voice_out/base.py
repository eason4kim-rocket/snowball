"""语音输出模块标准接口（ABC），Phase 3 实现"""

from abc import ABC, abstractmethod


class VoiceOutBase(ABC):
    """所有语音输出实现必须遵循的接口"""

    @abstractmethod
    async def speak(self, text: str) -> None:
        """将文字转为语音播放"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """停止当前播放"""
        ...
