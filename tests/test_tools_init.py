"""tools 工具注册单元测试"""

from tools import create_all_tools


class TestCreateAllTools:
    def test_returns_list(self):
        tools = create_all_tools()
        assert isinstance(tools, list)

    def test_tool_count(self):
        tools = create_all_tools()
        assert len(tools) == 7  # accessibility, applescript, mac_control, music, read_mem, search_mem, write_mem

    def test_custom_memory_path(self, tmp_path):
        custom = str(tmp_path / "custom_memory.md")
        tools = create_all_tools(memory_path=custom)
        assert len(tools) == 7
        # 验证 memory_path 已被配置（通过模块级变量）
        from tools.memory_tool import _memory_path
        assert _memory_path == custom
