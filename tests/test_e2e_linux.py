"""Linux 端到端测试 — 验证不依赖 macOS 的核心功能"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from tools.memory_tool import configure_memory_path, read_memory_tool, search_memory_tool, write_memory_tool

_read = read_memory_tool.handler
_search = search_memory_tool.handler
_write = write_memory_tool.handler


# ── EdgeTTS 实际生成音频测试 ──


class TestEdgeTTSAudioGeneration:
    """验证 Edge-TTS 能在 Linux 上实际生成音频文件"""

    def test_edge_tts_generate_audio(self):
        """实际调用 Edge-TTS API 生成 mp3 音频"""
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = f.name

        try:
            communicate = edge_tts.Communicate("你好老大", "zh-CN-XiaoxiaoNeural")
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(communicate.save(temp_path))
            finally:
                loop.close()

            # 验证文件存在且不为空
            assert os.path.exists(temp_path)
            size = os.path.getsize(temp_path)
            assert size > 0, f"生成的音频文件为空 (size={size})"
            print(f"  Edge-TTS 生成音频成功: {size} bytes")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_edge_speaker_init(self):
        """验证 EdgeTTSSpeaker 初始化参数正确"""
        from modules.voice_out.edge_speaker import EdgeTTSSpeaker

        speaker = EdgeTTSSpeaker(voice="zh-CN-YunxiNeural", max_length=100)
        assert speaker._voice == "zh-CN-YunxiNeural"
        assert speaker._max_length == 100
        assert speaker._playing is False


# ── 记忆系统全流程测试 ──


class TestMemorySystemE2E:
    """端到端验证记忆系统：配置 → 写入 → 搜索 → 读取 → 追加 → 覆盖"""

    @pytest.fixture(autouse=True)
    def setup_memory(self, tmp_path):
        self.memory_path = tmp_path / "e2e_memory.md"
        configure_memory_path(str(self.memory_path))
        yield

    def run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_full_memory_lifecycle(self):
        """完整记忆生命周期：不存在 → 创建 → 追加 → 搜索 → 覆盖"""
        # 1. 文件不存在时读取
        result = self.run(_read({}))
        assert result == {"result": "记忆文件不存在"}

        # 2. 写入初始记忆
        result = self.run(_write({
            "content": "# 雪球的记忆\n\n## 老大的偏好\n- 语言：中文\n- 称呼：老大"
        }))
        assert result == {"result": "记忆已更新"}

        # 3. 读取验证
        result = self.run(_read({}))
        assert "老大的偏好" in result["result"]
        assert "语言：中文" in result["result"]

        # 4. 追加新记忆
        result = self.run(_write({
            "content": "## 音乐偏好\n- 最爱：周杰伦\n- 播放器：AlgerMusicPlayer",
            "append": True,
        }))
        assert result == {"result": "记忆已更新"}

        # 5. 搜索关键词
        result = self.run(_search({"keyword": "周杰伦"}))
        assert "周杰伦" in result["result"]

        # 6. 按章节搜索
        result = self.run(_search({"section": "音乐偏好"}))
        assert "AlgerMusicPlayer" in result["result"]
        assert "老大的偏好" not in result["result"]  # 不应包含其他章节

        # 7. 搜索不存在的关键词
        result = self.run(_search({"keyword": "不存在的东西"}))
        assert "未找到" in result["result"]

        # 8. 覆盖写入
        result = self.run(_write({
            "content": "# 全新记忆\n- 重置成功",
            "append": False,
        }))
        assert result == {"result": "记忆已更新"}

        # 9. 验证覆盖生效
        result = self.run(_read({}))
        assert "全新记忆" in result["result"]
        assert "周杰伦" not in result["result"]  # 旧内容已被覆盖

    def test_memory_path_switch(self, tmp_path):
        """验证运行时切换记忆路径"""
        path_a = tmp_path / "memory_a.md"
        path_b = tmp_path / "memory_b.md"

        # 写入 path_a
        configure_memory_path(str(path_a))
        self.run(_write({"content": "记忆文件 A"}))

        # 写入 path_b
        configure_memory_path(str(path_b))
        self.run(_write({"content": "记忆文件 B"}))

        # 切回 path_a 验证
        configure_memory_path(str(path_a))
        result = self.run(_read({}))
        assert "记忆文件 A" in result["result"]

        # 切回 path_b 验证
        configure_memory_path(str(path_b))
        result = self.run(_read({}))
        assert "记忆文件 B" in result["result"]


# ── Agent 记忆刷新测试 ──


class TestAgentMemoryRefresh:
    """验证 Agent 的记忆 hash 缓存和自动刷新机制"""

    def test_memory_hash_caching(self, tmp_path):
        """验证记忆 hash 缓存避免重复刷新"""
        from modules.agent.snowball_agent import SnowballAgent

        memory_file = tmp_path / "test_mem.md"
        memory_file.write_text("# 初始记忆\n", encoding="utf-8")

        agent = SnowballAgent(memory_path=str(memory_file))
        assert agent._last_memory_hash == 0

        # 模拟 client
        mock_client = MagicMock()
        mock_client.options = MagicMock()
        mock_client.options.system_prompt = ""

        # 第一次刷新 — 应更新 hash
        agent._refresh_memory_if_changed(mock_client)
        first_hash = agent._last_memory_hash
        assert first_hash != 0
        assert "初始记忆" in mock_client.options.system_prompt

        # 第二次刷新（无变化）— hash 不变，prompt 不重建
        mock_client.options.system_prompt = "should not change"
        agent._refresh_memory_if_changed(mock_client)
        assert agent._last_memory_hash == first_hash
        assert mock_client.options.system_prompt == "should not change"

        # 修改记忆文件 — 应更新
        memory_file.write_text("# 更新后的记忆\n", encoding="utf-8")
        agent._refresh_memory_if_changed(mock_client)
        assert agent._last_memory_hash != first_hash
        assert "更新后的记忆" in mock_client.options.system_prompt


# ── main.py 启动逻辑测试 ──


class TestMainStartup:
    """验证 main.py 的配置加载和 TTS 引擎选择逻辑"""

    def test_config_loading(self):
        """验证 config.yaml 正确加载"""
        from main import load_config

        config = load_config("config.yaml")
        assert config["agent"]["base_url"] == "http://localhost:11434/v1"
        assert config["agent"]["model"] == "qwen3.5:9b"
        assert config["voice_out"]["engine"] in ("macos_say", "edge_tts", "kokoro")

    def test_tts_engine_selection_edge(self):
        """验证 edge_tts 引擎正确选择"""
        from modules.voice_out import EdgeTTSSpeaker, VoiceOutBase

        speaker = EdgeTTSSpeaker(voice="zh-CN-XiaoxiaoNeural", max_length=50)
        assert isinstance(speaker, VoiceOutBase)
        assert speaker._voice == "zh-CN-XiaoxiaoNeural"

    def test_tts_engine_selection_kokoro(self):
        """验证 kokoro 引擎正确选择"""
        from modules.voice_out import KokoroSpeaker, VoiceOutBase

        speaker = KokoroSpeaker(voice="af_heart", max_length=50)
        assert isinstance(speaker, VoiceOutBase)
        assert speaker._voice == "af_heart"

    def test_tts_engine_selection_macos(self):
        """验证 macos_say 引擎正确选择"""
        from modules.voice_out import MacOSSaySpeaker, VoiceOutBase

        speaker = MacOSSaySpeaker(voice="Ting-Ting", max_length=50)
        assert isinstance(speaker, VoiceOutBase)
        assert speaker._voice == "Ting-Ting"

    def test_tool_creation_with_config_path(self):
        """验证工具创建使用配置路径"""
        from tools import create_all_tools
        import tools.memory_tool as mem_mod

        tools = create_all_tools(memory_path="/custom/path/MEMORY.md")
        assert len(tools) == 7
        assert mem_mod._memory_path == "/custom/path/MEMORY.md"
