"""AppleScript 工具 — 控制 macOS 应用（Music/Mail/Finder/Safari 等）"""

import subprocess

from open_agent_sdk import define_tool
from open_agent_sdk.types import ToolContext, ToolResult


async def _applescript_handler(input: dict, ctx: ToolContext) -> ToolResult:
    """执行 AppleScript 脚本"""
    script = input.get("script", "")
    app = input.get("app", "")

    # 如果指定了 app，包裹在 tell block 里
    if app:
        script = f'tell application "{app}"\n{script}\nend tell'

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return ToolResult(tool_use_id="", content=output or "执行成功")
    except subprocess.TimeoutExpired:
        return ToolResult(tool_use_id="", content="错误：AppleScript 执行超时", is_error=True)
    except Exception as e:
        return ToolResult(tool_use_id="", content=f"错误：{e}", is_error=True)


def create_applescript_tool():
    """创建 AppleScript 工具"""
    return define_tool(
        name="AppleScript",
        description=(
            "执行 AppleScript 控制 macOS 应用。"
            "支持：打开App、播放音乐、发邮件、控制 Finder/Safari 等。"
            "简单操作用这个，秒级完成。"
            "示例：app='Music', script='play'；app='Music', script='play playlist \"周杰伦\"'"
        ),
        input_schema={
            "properties": {
                "script": {
                    "type": "string",
                    "description": "AppleScript 代码片段",
                },
                "app": {
                    "type": "string",
                    "description": "目标应用名（可选），如 Music/Mail/Finder/Safari",
                },
            },
            "required": ["script"],
        },
        handler=_applescript_handler,
    )
