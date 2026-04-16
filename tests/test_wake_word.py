"""唤醒词检测器测试"""

from modules.voice_in.wake_word import WakeWordDetector


class TestWakeWordDetector:
    def test_default_wake_words(self):
        d = WakeWordDetector()
        assert "雪球" in d.wake_words
        assert "snowball" in d.wake_words

    def test_detect_chinese(self):
        d = WakeWordDetector()
        assert d.detect_in_text("雪球打开音乐")
        assert d.detect_in_text("嘿雪球")

    def test_detect_english(self):
        d = WakeWordDetector()
        assert d.detect_in_text("Snowball play music")
        assert d.detect_in_text("hey snowball")

    def test_no_wake_word(self):
        d = WakeWordDetector()
        assert not d.detect_in_text("打开音乐")
        assert not d.detect_in_text("hello")

    def test_disabled_always_true(self):
        d = WakeWordDetector(enabled=False)
        assert d.detect_in_text("anything at all")
        assert d.detect_in_text("")

    def test_strip_chinese(self):
        d = WakeWordDetector()
        assert d.strip_wake_word("雪球打开音乐") == "打开音乐"

    def test_strip_english(self):
        d = WakeWordDetector()
        result = d.strip_wake_word("snowball play music")
        assert result == "play music"

    def test_strip_with_comma(self):
        d = WakeWordDetector()
        assert d.strip_wake_word("雪球，打开音乐") == "打开音乐"

    def test_custom_words(self):
        d = WakeWordDetector(wake_words=["小助手"])
        assert d.detect_in_text("小助手帮我")
        assert not d.detect_in_text("雪球帮我")
