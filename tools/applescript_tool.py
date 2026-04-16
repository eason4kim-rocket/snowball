"""AppleScript 工具 — 控制 macOS 应用（Music/Mail/Finder/Safari 等）"""

import subprocess

from open_agent import tool

from .retry import with_retry


@tool(
    name="AppleScript",
    description=(
        "执行 AppleScript 控制 macOS 应用。"
        "支持：打开App、播放音乐、发邮件、控制 Finder/Safari 等。"
        "简单操作用这个，秒级完成。"
        "示例：app='Music', script='play'；app='Music', script='play playlist \"周杰伦\"'"
    ),
    input_schema={
        "type": "object",
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
)
@with_retry(max_retries=2, retry_delay=0.5)
async def applescript_tool(args: dict) -> dict:
    """执行 AppleScript 脚本（失败自动重试 2 次）"""
    script = args.get("script", "")
    app = args.get("app", "")

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
        return {"result": output or "执行成功"}
    except subprocess.TimeoutExpired:
        return {"error": "AppleScript 执行超时"}
    except Exception as e:
        return {"error": str(e)}
