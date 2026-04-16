"""Fazm 工具 — 通过分布式通知控制 Fazm App 执行复杂 GUI 操作"""

import json
import subprocess

from open_agent import tool

from .retry import with_retry

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


@tool(
    name="FazmControl",
    description=(
        "通过 Fazm App 执行复杂 GUI 操作（需要 Fazm 正在运行）。"
        "用于：点击按钮、填表单、跨App操作等 AppleScript 无法完成的任务。"
        "action='query'：直接注入文字查询给 Fazm（最常用）"
        "action='control'：发送控制命令（如 sendFollowUp:xxx）"
        "action='getState'：读取 Fazm 当前状态"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
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
)
@with_retry(max_retries=2, retry_delay=1.0)
async def fazm_tool(args: dict) -> dict:
    """通过 Fazm 执行 GUI 操作（失败自动重试 2 次）"""
    action = args.get("action", "query")
    text = args.get("text", "")

    try:
        if action == "query":
            text_json = json.dumps(text, ensure_ascii=False)
            swift_code = _FAZM_QUERY_TEMPLATE.format(text_json=text_json)
        elif action == "control":
            command = args.get("command", f"sendFollowUp:{text}")
            swift_code = _FAZM_CONTROL_TEMPLATE.format(command=command)
        elif action == "getState":
            swift_code = _FAZM_CONTROL_TEMPLATE.format(command="getState")
        else:
            return {"error": f"未知操作：{action}"}

        result = subprocess.run(
            ["xcrun", "swift", "-e", swift_code],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if action == "getState":
            try:
                with open(_STATE_FILE, "r") as f:
                    state = f.read()
                return {"result": state}
            except FileNotFoundError:
                return {"error": "Fazm 状态文件不存在，App 可能未运行"}

        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        return {"result": output or "命令已发送"}

    except subprocess.TimeoutExpired:
        return {"error": "Fazm 命令超时"}
    except Exception as e:
        return {"error": str(e)}
