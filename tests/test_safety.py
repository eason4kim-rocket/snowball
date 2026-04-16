"""工具安全边界测试"""

import asyncio

from tools.safety import SafetyGuard


class TestSafetyGuard:
    def test_safe_operation_no_confirm(self):
        guard = SafetyGuard()
        assert not guard.needs_confirmation("AppleScript", {"script": "play"})

    def test_dangerous_delete(self):
        guard = SafetyGuard()
        assert guard.needs_confirmation("AppleScript", {"script": "delete file"})

    def test_dangerous_send_mail(self):
        guard = SafetyGuard()
        assert guard.needs_confirmation("AppleScript", {"script": "send message", "app": "Mail"})

    def test_dangerous_mac_control_sleep(self):
        guard = SafetyGuard()
        assert guard.needs_confirmation("MacControl", {"operation": "sleep"})

    def test_dangerous_mac_control_lock(self):
        guard = SafetyGuard()
        assert guard.needs_confirmation("MacControl", {"operation": "lock"})

    def test_safe_mac_control_volume(self):
        guard = SafetyGuard()
        assert not guard.needs_confirmation("MacControl", {"operation": "volume_up"})

    def test_disabled_no_confirm(self):
        guard = SafetyGuard(enabled=False)
        assert not guard.needs_confirmation("AppleScript", {"script": "delete everything"})

    def test_describe_risk(self):
        guard = SafetyGuard()
        risk = guard.describe_risk("AppleScript", {"script": "delete file"})
        assert "AppleScript" in risk
        assert "删除" in risk or "delete" in risk.lower()

    def test_confirm_callback(self):
        """自定义确认回调（Web 模式）"""
        guard = SafetyGuard(confirm_callback=lambda name, risk: False)
        assert not asyncio.run(guard.confirm("AppleScript", {"script": "delete file"}))

    def test_confirm_callback_allow(self):
        guard = SafetyGuard(confirm_callback=lambda name, risk: True)
        assert asyncio.run(guard.confirm("AppleScript", {"script": "delete file"}))

    def test_safe_tool_auto_allow(self):
        guard = SafetyGuard()
        assert asyncio.run(guard.confirm("ReadMemory", {"path": "test.md"}))

    def test_unknown_tool_no_confirm(self):
        guard = SafetyGuard()
        assert not guard.needs_confirmation("UnknownTool", {"action": "anything"})
