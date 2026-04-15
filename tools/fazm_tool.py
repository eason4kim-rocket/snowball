"""Fazm 工具 — 通过分布式通知控制 Fazm App 执行复杂 GUI 操作"""

import json
import subprocess
import time

from open_agent_sdk import define_tool
from open_agent_sdk.types import ToolContext, ToolResult

# Fazm 分布式通知 Swift 代码模板
_FAZM_CONTROL_TEMPLATE = '''
import Foundation
DistributedNotificationCenter.default().postNotificationName(
    .init("com.fazm.control"), object: nil,
    userInfo: ["command": "{command}"],
    deliverImmediately: true
)
RunLoop.current.run(until: Date(timeIntervalSinceNow: 1.0))
'''

_FAZM_QUERY_TEMPLATE = '''
import Foundation
DistributedNotificationCenter.default().postNotificationName(
    .init("com.fazm.testQuery"), object: nil,
    userInfo: ["text": {text_json}],
    deliverImmediately: true
)
RunLoop.current.run(until: Date(timeIntervalSinceNow: 1.0))
'''

_STATE_FILE = "/tmp/fazm-control-state.json"


async def _fazm_handler(input: dict, ctx: ToolContext) -> ToolResult:
    """通过 Fazm 执行 GUI 操作"""
    action = input.get("action", "query")
    text = input.get("text", "")

    try:
        if action == "query":
            # 直接注入查询到 Fazm
            text_json = json.dumps(text, ensure_ascii=False)
            swift_code = _FAZM_QUERY_TEMPLATE.format(text_json=text_json)
        elif action == "control":
            # 发送控制命令
            command = input.get("command", f"sendFollowUp:{text}")
            swift_code = _FAZM_CONTROL_TEMPLATE.format(command=command)
        elif action == "getState":
            # 获取状态
            swift_code = _FAZM_CONTROL_TEMPLATE.format(command="getState")
        else:
            return ToolResult(tool_use_id="", content=f"未知操作：{action}", is_error=True)

        result = subprocess.run(
            ["xcrun", "swift", "-e", swift_code],
            capture_output=True,
            text=True,
            timeout=15,
        )

        # 如果是 getState，读取状态文件
        if action == "getState":
            try:
                with open(_STATE_FILE, "r") as f:
                    state = f.read()
                return ToolResult(tool_use_id="", content=state)
            except FileNotFoundError:
                return ToolResult(tool_use_id="", content="Fazm 状态文件不存在，App 可能未运行", is_error=True)

        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return ToolResult(tool_use_id="", content=output or "命令已发送")

    except subprocess.TimeoutExpired:
        return ToolResult(tool_use_id="", content="错误：Fazm 命令超时", is_error=True)
    except Exception as e:
        return ToolResult(tool_use_id="", content=f"错误：{e}", is_error=True)


def create_fazm_tool():
    """创建 Fazm 控制工具"""
    return define_tool(
        name="FazmControl",
        description=(
            "通过 Fazm App 执行复杂 GUI 操作（需要 Fazm 正在运行）。"
            "用于：点击按钮、填表单、跨App操作等 AppleScript 无法完成的任务。"
            "action='query'：直接注入文字查询给 Fazm（最常用）"
            "action='control'：发送控制命令（如 sendFollowUp:xxx）"
            "action='getState'：读取 Fazm 当前状态"
        ),
        input_schema={
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["query", "control", "getState"],
                    "description": "操作类型：query=注入查询, control=控制命令, getState=读取状态",
                },
                "text": {
                    "type": "string",
                    "description": "要发送的文字/命令内容",
                },
                "command": {
                    "type": "string",
                    "description": "control 模式的完整命令（如 sendFollowUp:xxx）",
                },
            },
            "required": ["action"],
        },
        handler=_fazm_handler,
    )
