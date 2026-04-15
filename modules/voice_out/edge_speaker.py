"""语音输出 — Edge-TTS 封装（微软免费 TTS API，质量最好）"""

from __future__ import annotations

import asyncio

import edge_tts


class EdgeTTSSpeaker:
    """基于 Edge-TTS 的自然语音输出（微软免费 API）"""

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", max_length: int = 50):
        self._voice = voice
        self._max_length = max_length
        self._playing = False

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
            self._playing = True

            # 生成音频流
            communicate = edge_tts.Communicate(text, self._voice)

            # 保存临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                temp_path = f.name

            await communicate.save(temp_path)

            # 播放
            import subprocess
            proc = subprocess.Popen(["afplay", temp_path])
            await asyncio.to_thread(proc.wait)

            # 删除临时文件
            import os
            os.unlink(temp_path)

        except Exception as e:
            print(f"Edge-TTS 错误: {e}")
        finally:
            self._playing = False

    async def stop(self) -> None:
        """停止当前播放"""
        self._playing = False
        import subprocess
        subprocess.run(["pkill", "afplay"], stderr=subprocess.DEVNULL)
