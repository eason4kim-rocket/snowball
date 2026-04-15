"""记忆工具 — 读写 SNOWBALL.md 记忆文件"""

from pathlib import Path

from open_agent_sdk import define_tool
from open_agent_sdk.types import ToolContext, ToolResult


def create_read_memory_tool(memory_path: str = "SNOWBALL.md"):
    """创建读取记忆工具"""

    async def _read_memory_handler(input: dict, ctx: ToolContext) -> ToolResult:
        path = Path(memory_path)
        if not path.exists():
            return ToolResult(tool_use_id="", content="记忆文件不存在")
        try:
            content = path.read_text(encoding="utf-8")
            return ToolResult(tool_use_id="", content=content)
        except Exception as e:
            return ToolResult(tool_use_id="", content=f"读取失败：{e}", is_error=True)

    return define_tool(
        name="ReadMemory",
        description="读取雪球的记忆文件（SNOWBALL.md），包含老大的偏好、常用操作等信息",
        input_schema={"properties": {}, "required": []},
        handler=_read_memory_handler,
        read_only=True,
    )


def create_write_memory_tool(memory_path: str = "SNOWBALL.md"):
    """创建写入记忆工具"""

    async def _write_memory_handler(input: dict, ctx: ToolContext) -> ToolResult:
        content = input.get("content", "")
        append = input.get("append", True)
        path = Path(memory_path)

        try:
            if append and path.exists():
                existing = path.read_text(encoding="utf-8")
                content = existing.rstrip() + "\n\n" + content
            path.write_text(content.strip() + "\n", encoding="utf-8")
            return ToolResult(tool_use_id="", content="记忆已更新")
        except Exception as e:
            return ToolResult(tool_use_id="", content=f"写入失败：{e}", is_error=True)

    return define_tool(
        name="WriteMemory",
        description=(
            "写入/追加内容到雪球的记忆文件（SNOWBALL.md）。"
            "append=true（默认）追加到末尾，append=false 覆盖整个文件。"
            "当老大告诉你新的偏好或信息时，主动调用此工具记住。"
        ),
        input_schema={
            "properties": {
                "content": {
                    "type": "string",
                    "description": "要写入/追加的内容（Markdown 格式）",
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式（默认 true），false 则覆盖整个文件",
                },
            },
            "required": ["content"],
        },
        handler=_write_memory_handler,
    )
