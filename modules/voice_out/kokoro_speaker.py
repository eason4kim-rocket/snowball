"""语音输出 — Kokoro TTS 封装（自然语音）"""

from __future__ import annotations

import asyncio
from pathlib import Path

from .base import VoiceOutBase

try:
    from kokoro_onnx import Kokoro
except ImportError:
    Kokoro = None  # type: ignore[misc,assignment]


class KokoroSpeaker(VoiceOutBase):
    """基于 Kokoro TTS 的自然语音输出（需安装 kokoro-onnx）"""

    def __init__(self, voice: str = "af_heart", max_length: int = 50):
        self._voice = voice
        self._max_length = max_length
        self._model = None
        self._playing = False

    async def _ensure_model(self):
        """懒加载模型"""
        if Kokoro is None:
            raise ImportError("kokoro-onnx 未安装，请运行: pip install kokoro-onnx")
        if self._model is not None:
            return self._model

        # 在后台线程加载模型（避免阻塞）
        loop = asyncio.get_running_loop()
        self._model = await loop.run_in_executor(
            None, lambda: Kokoro("kokoro-v0_19.onnx", device="cpu")
        )
        return self._model

    async def speak(self, text: str) -> None:
        """将文字转为语音播放"""
        # 截短回复
        if len(text) > self._max_length:
            sentences = text.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
            text = "".join(sentences[:2]).strip()
            if len(text) > self._max_length:
                text = text[: self._max_length] + "..."

        print(f" 🔊 {text}")

        try:
            model = await self._ensure_model()
            self._playing = True

            # 在后台线程生成音频
            loop = asyncio.get_running_loop()
            audio = await loop.run_in_executor(
                None, lambda: model(text, voice=self._voice)
            )

            # 保存临时文件并播放
            temp_path = Path("/tmp/snowball_tts.wav")
            audio.save(temp_path)

            # 用系统播放器播放
            import subprocess
            proc = subprocess.Popen(["afplay", str(temp_path)])
            await asyncio.to_thread(proc.wait)

        except Exception as e:
            print(f"Kokoro TTS 错误: {e}")
        finally:
            self._playing = False

    async def stop(self) -> None:
        """停止当前播放"""
        self._playing = False
        # 停止 afplay 进程
        import subprocess
        subprocess.run(["pkill", "afplay"], stderr=subprocess.DEVNULL)
