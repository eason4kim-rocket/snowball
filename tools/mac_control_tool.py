"""Mac 控制工具 — macOS 系统快捷操作（音量/亮度/窗口等）"""

import subprocess

from open_agent_sdk import define_tool
from open_agent_sdk.types import ToolContext, ToolResult


async def _mac_control_handler(input: dict, ctx: ToolContext) -> ToolResult:
    """执行 macOS 系统控制"""
    operation = input.get("operation", "")
    value = input.get("value", "")

    scripts = {
        "volume_up": "set volume output volume (output volume of settings + 10)",
        "volume_down": "set volume output volume (output volume of settings - 10)",
        "volume_set": f"set volume output volume {value}" if value else None,
        "mute": "set volume output muted true",
        "unmute": "set volume output muted false",
        "brightness_up": None,  # 需要额外工具
        "open_app": f'tell application "{value}" to activate' if value else None,
        "quit_app": f'quit application "{value}"' if value else None,
        "sleep": 'tell application "System Events" to sleep',
        "lock": 'tell application "System Events" to keystroke "q" using {control down, command down}',
    }

    if operation in ("brightness_up", "brightness_down"):
        # 亮度控制用 AppleScript + 按键模拟
        key = "2" if operation == "brightness_down" else "1"
        script = f'tell application "System Events" to key code {key} using {{option down, shift down}}'
    elif operation in scripts and scripts[operation]:
        script = scripts[operation]
    elif operation == "custom":
        script = value
    else:
        return ToolResult(tool_use_id="", content=f"未知操作：{operation}", is_error=True)

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return ToolResult(tool_use_id="", content=output or f"已执行：{operation}")
    except subprocess.TimeoutExpired:
        return ToolResult(tool_use_id="", content="错误：操作超时", is_error=True)
    except Exception as e:
        return ToolResult(tool_use_id="", content=f"错误：{e}", is_error=True)


def create_mac_control_tool():
    """创建 macOS 系统控制工具"""
    return define_tool(
        name="MacControl",
        description=(
            "macOS 系统快捷控制。"
            "operation: volume_up/volume_down/volume_set/mute/unmute/"
            "open_app/quit_app/sleep/lock/brightness_up/brightness_down/custom"
            "value: 操作参数（如音量值0-100、App名称、自定义AppleScript）"
        ),
        input_schema={
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
        handler=_mac_control_handler,
    )
