"""唤醒词检测 — 可选的 wake word 模块，减少 always-listening 的 CPU 占用。

支持两种模式：
1. 简单文本匹配（零依赖）：检查 STT 转写结果是否包含唤醒词
2. openWakeWord（可选）：音频级检测，无需 STT 即可唤醒

用法::

    detector = WakeWordDetector(wake_words=["雪球", "snowball"])

    # 模式 1：文本匹配（配合 RealtimeSTT）
    if detector.detect_in_text("雪球打开音乐"):
        command = detector.strip_wake_word("雪球打开音乐")
        # command = "打开音乐"

    # 模式 2：启用/禁用
    detector.enabled = False  # 关闭唤醒词，回到 always-listening
"""

from __future__ import annotations


class WakeWordDetector:
    """唤醒词检测器（文本匹配模式，零依赖）"""

    def __init__(
        self,
        wake_words: list[str] | None = None,
        enabled: bool = True,
    ):
        self._wake_words = [w.lower() for w in (wake_words or ["雪球", "snowball"])]
        self.enabled = enabled

    @property
    def wake_words(self) -> list[str]:
        return list(self._wake_words)

    def detect_in_text(self, text: str) -> bool:
        """检查文本是否包含唤醒词。未启用时始终返回 True（透传）。"""
        if not self.enabled:
            return True
        text_lower = text.lower().strip()
        return any(w in text_lower for w in self._wake_words)

    def strip_wake_word(self, text: str) -> str:
        """从文本中移除唤醒词，返回实际命令部分。"""
        result = text.strip()
        for w in self._wake_words:
            # 不区分大小写替换
            lower = result.lower()
            idx = lower.find(w)
            if idx != -1:
                result = result[:idx] + result[idx + len(w):]
        # 清理多余标点和空格
        result = result.strip().lstrip("，,、 ")
        return result
