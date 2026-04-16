"""Mac 控制工具 — macOS 系统快捷操作（音量/亮度/窗口等）"""

import subprocess

from open_agent import tool

from .retry import with_retry


@tool(
    name="MacControl",
    description=(
        "macOS 系统快捷控制。"
        "operation: volume_up/volume_down/volume_set/mute/unmute/"
        "open_app/quit_app/sleep/lock/brightness_up/brightness_down/custom"
        "value: 操作参数（如音量值0-100、App名称、自定义AppleScript）"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "description": "操作名：volume_up, volume_down, volume_set, mute, unmute, open_app, quit_app, sleep, lock, brightness_up, brightness_down, custom",
            },
            "value": {
                "type": "string",
                "description": "操作参数：音量值(0-100)、App名称、自定义脚本",
            },
        },
        "required": ["operation"],
    },
)
@with_retry(max_retries=2, retry_delay=0.5)
async def mac_control_tool(args: dict) -> dict:
    """执行 macOS 系统控制（失败自动重试 2 次）"""
    operation = args.get("operation", "")
    value = args.get("value", "")

    scripts = {
        "volume_up": "set volume output volume (output volume of settings + 10)",
        "volume_down": "set volume output volume (output volume of settings - 10)",
        "volume_set": f"set volume output volume {value}" if value else None,
        "mute": "set volume output muted true",
        "unmute": "set volume output muted false",
        "open_app": f'tell application "{value}" to activate' if value else None,
        "quit_app": f'quit application "{value}"' if value else None,
        "sleep": 'tell application "System Events" to sleep',
        "lock": 'tell application "System Events" to keystroke "q" using {control down, command down}',
    }

    if operation in ("brightness_up", "brightness_down"):
        key = "2" if operation == "brightness_down" else "1"
        script = f'tell application "System Events" to key code {key} using {{option down, shift down}}'
    elif operation in scripts and scripts[operation]:
        script = scripts[operation]
    elif operation == "custom":
        script = value
    else:
        return {"error": f"未知操作：{operation}"}

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return {"result": output or f"已执行：{operation}"}
    except subprocess.TimeoutExpired:
        return {"error": "操作超时"}
    except Exception as e:
        return {"error": str(e)}
