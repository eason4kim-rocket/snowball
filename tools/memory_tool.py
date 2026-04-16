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
    name="SearchMemory",
    description=(
        "搜索雪球记忆文件中的特定章节或关键词。"
        "keyword：搜索关键词，返回包含该关键词的所有行及上下文。"
        "section：按 ## 标题搜索特定章节内容。"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {
                "type": "string",
                "description": "搜索关键词",
            },
            "section": {
                "type": "string",
                "description": "章节标题（如 '老大的偏好'、'常用操作'）",
            },
        },
        "required": [],
    },
)
async def search_memory_tool(args: dict) -> dict:
    """搜索记忆文件"""
    path = Path(_memory_path)
    if not path.exists():
        return {"result": "记忆文件不存在"}

    try:
        content = path.read_text(encoding="utf-8")
        keyword = args.get("keyword", "")
        section = args.get("section", "")

        if section:
            # 按章节搜索
            lines = content.split("\n")
            result_lines: list[str] = []
            in_section = False
            for line in lines:
                if line.startswith("## ") and section in line:
                    in_section = True
                    result_lines.append(line)
                elif line.startswith("## ") and in_section:
                    break
                elif in_section:
                    result_lines.append(line)
            if result_lines:
                return {"result": "\n".join(result_lines).strip()}
            return {"result": f"未找到章节：{section}"}

        if keyword:
            # 按关键词搜索
            matches = [line for line in content.split("\n") if keyword in line]
            if matches:
                return {"result": "\n".join(matches)}
            return {"result": f"未找到关键词：{keyword}"}

        return {"result": content}
    except Exception as e:
        return {"error": f"搜索失败：{e}"}


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
