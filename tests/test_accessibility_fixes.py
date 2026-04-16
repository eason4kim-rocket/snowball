"""AccessibilityControl A 方案修复测试 — 权限检查 + 错误码识别"""

import sys

import pytest

# tools/__init__.py 用 `from .accessibility_tool import accessibility_tool`
# 把 Tool 对象绑到了 `tools.accessibility_tool` 名字上，覆盖了同名子模块。
# 测试里要通过 sys.modules 拿到真正的模块。
import tools.accessibility_tool  # noqa: F401  触发模块加载
ax_mod = sys.modules["tools.accessibility_tool"]

_parse_applescript_error = ax_mod._parse_applescript_error


class TestErrorCodeParsing:
    def test_no_permission_error_recognized(self):
        stderr = '72:78: execution error: "System Events"遇到一个错误： (-1719)'
        r = _parse_applescript_error(stderr)
        assert r["error_kind"] == "no_ax_permission"
        assert r["error_code"] == "-1719"
        assert "辅助功能" in r["error"]

    def test_element_not_found(self):
        stderr = 'error: "System Events"遇到一个错误： (-1728)'
        r = _parse_applescript_error(stderr)
        assert r["error_kind"] == "element_not_found"
        assert r["error_code"] == "-1728"

    def test_app_not_running(self):
        stderr = 'error: 应用程序无法打开 (-10810)'
        r = _parse_applescript_error(stderr)
        assert r["error_kind"] == "app_not_running"

    def test_unknown_error_passthrough(self):
        stderr = '一些未知错误 (-99999)'
        r = _parse_applescript_error(stderr)
        assert "error_kind" not in r
        assert r["error"] == stderr


class TestPermissionCheck:
    def test_permission_check_returns_bool(self):
        """权限检查至少要返回 True/False，不能抛异常"""
        ax_mod._AX_PERMISSION_CACHE = None
        result = ax_mod._check_ax_permission()
        assert isinstance(result, bool)


@pytest.mark.asyncio
class TestPermissionGating:
    async def test_list_apps_works_without_permission(self, monkeypatch):
        """list_apps 不触发权限检查"""
        monkeypatch.setattr(ax_mod, "_check_ax_permission", lambda: False)
        r = await ax_mod.accessibility_tool.handler({"action": "list_apps"})
        assert r.get("error_kind") != "no_ax_permission"

    async def test_click_blocked_without_permission(self, monkeypatch):
        """click 在无权限时直接返回结构化错误，不会去跑 osascript"""
        monkeypatch.setattr(ax_mod, "_check_ax_permission", lambda: False)
        r = await ax_mod.accessibility_tool.handler({
            "action": "click",
            "app": "Finder",
            "element_name": "x",
        })
        assert r.get("error_kind") == "no_ax_permission"
        assert "辅助功能" in r["error"]
