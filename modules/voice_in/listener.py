"""语音输入 — RealtimeSTT 封装（always-listening，无需唤醒词）"""

from __future__ import annotations

import asyncio
from typing import Callable

from RealtimeSTT import AudioToTextRecorder

from .base import VoiceInBase


class RealtimeSTTListener(VoiceInBase):
    """基于 RealtimeSTT 的 always-listening 语音输入"""

    def __init__(
        self,
        language: str = "zh",
        model: str = "tiny",
        silero_sensitivity: float = 0.4,
        post_speech_silence_duration: float = 0.6,
    ):
        self._language = language
        self._model = model
        self._silero_sensitivity = silero_sensitivity
        self._post_speech_silence_duration = post_speech_silence_duration
        self._recorder: AudioToTextRecorder | None = None
        self._on_text: Callable[[str], None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _on_transcription(self, text: str) -> None:
        """RealtimeSTT 回调：检测到语音转文字后触发"""
        text = text.strip()
        if text and self._on_text and self._loop:
            # 从 STT 线程调度到 asyncio 事件循环
            asyncio.run_coroutine_threadsafe(
                self._async_on_text(text), self._loop
            )

    async def _async_on_text(self, text: str) -> None:
        """在 asyncio 事件循环中执行回调"""
        if self._on_text:
            self._on_text(text)

    async def start_listening(self, on_text: Callable[[str], None]) -> None:
        """开始持续监听"""
        self._on_text = on_text
        self._loop = asyncio.get_event_loop()

        self._recorder = AudioToTextRecorder(
            model=self._model,
            language=self._language,
            silero_sensitivity=self._silero_sensitivity,
            post_speech_silence_duration=self._post_speech_silence_duration,
            on_recording_start=lambda: print(" 🎤 听到声音...", end="", flush=True),
            on_recording_stop=lambda: print(" 处理中...", end="", flush=True),
            spinner=False,
            enable_realtime_transcription=False,
            use_microphone=True,
        )

        # 在后台线程运行 STT 循环
        import threading
        self._thread = threading.Thread(target=self._stt_loop, daemon=True)
        self._thread.start()
        print("🎤 语音监听已启动（always-listening，无需唤醒词）")

    def _stt_loop(self) -> None:
        """STT 循环：持续监听并转写"""
        while self._recorder:
            try:
                text = self._recorder.text(self._on_transcription)
            except Exception as e:
                print(f"\nSTT 错误: {e}")
                break

    async def stop_listening(self) -> None:
        """停止监听"""
        if self._recorder:
            self._recorder.shutdown()
            self._recorder = None
        print("🎤 语音监听已停止")
