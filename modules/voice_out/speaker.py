"""语音输出 — macOS say + RealtimeTTS 封装"""

from __future__ import annotations

import subprocess

from .base import VoiceOutBase


class MacOSSaySpeaker(VoiceOutBase):
    """基于 macOS say 命令的语音输出（零配置，支持中文 Ting-Ting）"""

    def __init__(self, voice: str = "Ting-Ting", max_length: int = 50):
        self._voice = voice
        self._max_length = max_length
        self._process: subprocess.Popen | None = None

    async def speak(self, text: str) -> None:
        """将文字转为语音播放"""
        # 截短回复
        if len(text) > self._max_length:
            # 取前两句
            sentences = text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
            text = "".join(sentences[:2]).strip()
            if len(text) > self._max_length:
                text = text[: self._max_length] + "..."

        print(f" 🔊 {text}")

        try:
            self._process = subprocess.Popen(
                ["say", "-v", self._voice, text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._process.wait()
        except Exception as e:
            print(f"TTS 错误: {e}")
        finally:
            self._process = None

    async def stop(self) -> None:
        """停止当前播放"""
        if self._process:
            self._process.terminate()
            self._process = None
