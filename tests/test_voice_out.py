"""voice_out 模块接口测试"""

from modules.voice_out.base import VoiceOutBase
from modules.voice_out.speaker import MacOSSaySpeaker
from modules.voice_out.edge_speaker import EdgeTTSSpeaker
from modules.voice_out.kokoro_speaker import KokoroSpeaker


class TestVoiceOutInheritance:
    """验证所有 TTS 实现都继承 VoiceOutBase"""

    def test_macos_say_inherits(self):
        assert issubclass(MacOSSaySpeaker, VoiceOutBase)

    def test_edge_tts_inherits(self):
        assert issubclass(EdgeTTSSpeaker, VoiceOutBase)

    def test_kokoro_inherits(self):
        assert issubclass(KokoroSpeaker, VoiceOutBase)

    def test_macos_say_instance(self):
        speaker = MacOSSaySpeaker()
        assert isinstance(speaker, VoiceOutBase)

    def test_edge_tts_instance(self):
        speaker = EdgeTTSSpeaker()
        assert isinstance(speaker, VoiceOutBase)

    def test_kokoro_instance(self):
        speaker = KokoroSpeaker()
        assert isinstance(speaker, VoiceOutBase)


class TestVoiceOutExports:
    """验证 __init__.py 正确导出所有类"""

    def test_exports(self):
        from modules.voice_out import __all__
        assert "VoiceOutBase" in __all__
        assert "MacOSSaySpeaker" in __all__
        assert "EdgeTTSSpeaker" in __all__
        assert "KokoroSpeaker" in __all__
