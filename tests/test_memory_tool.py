"""memory_tool 单元测试"""

import asyncio

import pytest

from tools.memory_tool import (
    configure_memory_path,
    read_memory_tool,
    search_memory_tool,
    write_memory_tool,
)

# @tool 装饰器将函数包装为 Tool 对象，用 .handler 访问原始异步函数
_read = read_memory_tool.handler
_search = search_memory_tool.handler
_write = write_memory_tool.handler


@pytest.fixture(autouse=True)
def tmp_memory(tmp_path):
    """每个测试使用独立的临时记忆文件"""
    path = tmp_path / "TEST_MEMORY.md"
    configure_memory_path(str(path))
    yield path


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestReadMemory:
    def test_file_not_exist(self):
        result = run(_read({}))
        assert result == {"result": "记忆文件不存在"}

    def test_read_existing(self, tmp_memory):
        tmp_memory.write_text("# 测试记忆\n- 偏好：中文\n", encoding="utf-8")
        result = run(_read({}))
        assert "测试记忆" in result["result"]
        assert "偏好" in result["result"]


class TestSearchMemory:
    def test_search_by_keyword(self, tmp_memory):
        tmp_memory.write_text("# 雪球的记忆\n## 老大的偏好\n- 语言：中文\n- 音乐：周杰伦\n", encoding="utf-8")
        result = run(_search({"keyword": "周杰伦"}))
        assert "周杰伦" in result["result"]

    def test_search_by_section(self, tmp_memory):
        tmp_memory.write_text(
            "# 雪球的记忆\n## 老大的偏好\n- 语言：中文\n## 常用操作\n- 打开音乐\n",
            encoding="utf-8",
        )
        result = run(_search({"section": "老大的偏好"}))
        assert "语言" in result["result"]
        assert "打开音乐" not in result["result"]

    def test_search_missing_keyword(self, tmp_memory):
        tmp_memory.write_text("# 测试\n", encoding="utf-8")
        result = run(_search({"keyword": "不存在的内容"}))
        assert "未找到" in result["result"]

    def test_search_file_not_exist(self):
        result = run(_search({"keyword": "test"}))
        assert result == {"result": "记忆文件不存在"}


class TestWriteMemory:
    def test_write_new_file(self, tmp_memory):
        result = run(_write({"content": "# 新记忆"}))
        assert result == {"result": "记忆已更新"}
        assert tmp_memory.exists()
        assert "新记忆" in tmp_memory.read_text(encoding="utf-8")

    def test_append_mode(self, tmp_memory):
        tmp_memory.write_text("# 原始内容\n", encoding="utf-8")
        run(_write({"content": "## 追加内容", "append": True}))
        content = tmp_memory.read_text(encoding="utf-8")
        assert "原始内容" in content
        assert "追加内容" in content

    def test_overwrite_mode(self, tmp_memory):
        tmp_memory.write_text("# 原始内容\n", encoding="utf-8")
        run(_write({"content": "# 全新内容", "append": False}))
        content = tmp_memory.read_text(encoding="utf-8")
        assert "原始内容" not in content
        assert "全新内容" in content


class TestConfigureMemoryPath:
    def test_path_takes_effect(self, tmp_path):
        custom = tmp_path / "custom.md"
        custom.write_text("自定义路径内容\n", encoding="utf-8")
        configure_memory_path(str(custom))
        result = run(_read({}))
        assert "自定义路径内容" in result["result"]
