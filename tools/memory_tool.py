"""记忆工具 — 读写 SNOWBALL.md 记忆文件"""

from pathlib import Path

from open_agent import tool

# 默认路径，可通过 configure_memory_path() 覆盖
_memory_path: str = "SNOWBALL.md"


def configure_memory_path(path: str) -> None:
    """设置记忆文件路径（由 create_all_tools 调用）"""
    global _memory_path
    _memory_path = path


@tool(
    name="ReadMemory",
    description="读取雪球的记忆文件（SNOWBALL.md），包含老大的偏好、常用操作等信息",
    input_schema={"type": "object", "properties": {}, "required": []},
)
async def read_memory_tool(args: dict) -> dict:
    """读取记忆文件"""
    path = Path(_memory_path)
    if not path.exists():
        return {"result": "记忆文件不存在"}
    try:
        content = path.read_text(encoding="utf-8")
        return {"result": content}
    except Exception as e:
        return {"error": f"读取失败：{e}"}


@tool(
    name="WriteMemory",
    description=(
        "写入/追加内容到雪球的记忆文件（SNOWBALL.md）。"
        "append=true（默认）追加到末尾，append=false 覆盖整个文件。"
        "当老大告诉你新的偏好或信息时，主动调用此工具记住。"
    ),
    input_schema={
        "type": "object",
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
)
async def write_memory_tool(args: dict) -> dict:
    """写入记忆文件"""
    content = args.get("content", "")
    append = args.get("append", True)
    path = Path(_memory_path)

    try:
        if append and path.exists():
            existing = path.read_text(encoding="utf-8")
            content = existing.rstrip() + "\n\n" + content
        path.write_text(content.strip() + "\n", encoding="utf-8")
        return {"result": "记忆已更新"}
    except Exception as e:
        return {"error": f"写入失败：{e}"}
