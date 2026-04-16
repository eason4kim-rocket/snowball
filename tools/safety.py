"""工具安全边界 — 高风险操作确认机制。

在终端模式下，高风险操作会弹出确认提示；
在 Web Dashboard 模式下，通过回调函数让前端确认。

用法::

    guard = SafetyGuard()

    # 检查操作是否需要确认
    if guard.needs_confirmation(tool_name, args):
        risk = guard.describe_risk(tool_name, args)
        # 终端模式：直接 input() 确认
        # Web 模式：推送给前端确认
"""

from __future__ import annotations

import asyncio
import re
from typing import Callable


# 高风险操作模式匹配
_DANGEROUS_PATTERNS = {
    "AppleScript": [
        # 删除/移动文件
        r"(?i)(delete|remove|trash|移除|删除)",
        # 发送邮件/消息
        r"(?i)(send|mail|邮件|发送)",
        # 关机/重启/休眠
        r"(?i)(shut\s*down|restart|reboot|关机|重启)",
    ],
    "MacControl": [
        # 危险的系统操作
        r"(?i)(sleep|lock|quit_app|关机|锁屏)",
    ],
    "FazmControl": [
        # Fazm 可以执行任意 GUI 操作，所有 query 都有一定风险
        # 但只标记明确的危险模式
        r"(?i)(delete|删除|remove|移除|format|格式化)",
    ],
}

# 风险描述
_RISK_DESCRIPTIONS = {
    "delete": "将删除文件或数据",
    "send": "将发送邮件/消息",
    "shutdown": "将关闭/重启电脑",
    "sleep": "将使电脑休眠",
    "lock": "将锁定电脑",
    "quit": "将关闭应用",
    "format": "将格式化数据",
    "remove": "将移除/删除内容",
}


class SafetyGuard:
    """工具安全边界守卫"""

    def __init__(
        self,
        enabled: bool = True,
        confirm_callback: Callable[[str, str], bool] | None = None,
    ):
        """
        参数:
            enabled: 是否启用安全检查
            confirm_callback: 自定义确认回调（Web 模式用），
                              接收 (tool_name, risk_description) 返回 bool
                              为 None 时使用终端 input() 确认
        """
        self.enabled = enabled
        self._confirm_callback = confirm_callback

    def needs_confirmation(self, tool_name: str, args: dict) -> bool:
        """检查操作是否需要用户确认"""
        if not self.enabled:
            return False

        patterns = _DANGEROUS_PATTERNS.get(tool_name, [])
        if not patterns:
            return False

        # 将所有参数拼接成一个字符串用于检测
        args_text = " ".join(str(v) for v in args.values())

        return any(re.search(p, args_text) for p in patterns)

    def describe_risk(self, tool_name: str, args: dict) -> str:
        """描述操作的风险"""
        args_text = " ".join(str(v) for v in args.values()).lower()

        risks = []
        for key, desc in _RISK_DESCRIPTIONS.items():
            if key in args_text:
                risks.append(desc)

        if not risks:
            risks.append("此操作可能有风险")

        return f"⚠️ {tool_name}: {'; '.join(risks)}"

    async def confirm(self, tool_name: str, args: dict) -> bool:
        """请求用户确认。返回 True 表示允许执行。

        为避免阻塞 async 事件循环（尤其 voice_mode 下 STT 回调会堆积），
        终端 input() 放到 asyncio.to_thread 中执行。
        """
        if not self.needs_confirmation(tool_name, args):
            return True

        risk = self.describe_risk(tool_name, args)

        if self._confirm_callback:
            # 回调可以是同步或异步
            result = self._confirm_callback(tool_name, risk)
            if asyncio.iscoroutine(result):
                return await result
            return result

        # 终端模式：在线程池里跑 input()，不阻塞事件循环
        print(f"\n{risk}")
        print(f"  参数: {args}")
        response = await asyncio.to_thread(
            lambda: input("  确认执行？(y/N) > ").strip().lower()
        )
        return response in ("y", "yes", "是")
