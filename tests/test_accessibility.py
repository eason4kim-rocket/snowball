"""AccessibilityControl 工具单元测试

在 Linux 上测试参数校验和路由逻辑（不依赖 macOS osascript）。
"""

import asyncio
from unittest.mock import patch

from tools.accessibility_tool import accessibility_tool, _run_applescript


class TestAccessibilityToolRouting:
    """测试 action 路由和参数校验"""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_unknown_action(self):
        result = self._run(accessibility_tool.handler({"action": "unknown_action"}))
        assert "error" in result
        assert "未知操作" in result["error"]

    def test_list_elements_requires_app(self):
        result = self._run(accessibility_tool.handler({"action": "list_elements"}))
        assert "error" in result
        assert "app" in result["error"]

    def test_click_requires_app(self):
        result = self._run(accessibility_tool.handler({"action": "click"}))
        assert "error" in result
        assert "app" in result["error"]

    def test_type_text_requires_text(self):
        result = self._run(accessibility_tool.handler({"action": "type_text"}))
        assert "error" in result
        assert "text" in result["error"]

    def test_read_value_requires_app(self):
        result = self._run(accessibility_tool.handler({"action": "read_value"}))
        assert "error" in result
        assert "app" in result["error"]

    def test_set_value_requires_app_and_text(self):
        result = self._run(accessibility_tool.handler({"action": "set_value", "app": "Safari"}))
        assert "error" in result
        assert "text" in result["error"]

    def test_key_press_requires_keys(self):
        result = self._run(accessibility_tool.handler({"action": "key_press"}))
        assert "error" in result
        assert "keys" in result["error"]

    def test_menu_click_requires_app_and_path(self):
        result = self._run(accessibility_tool.handler({"action": "menu_click", "app": "Finder"}))
        assert "error" in result
        assert "menu_path" in result["error"]

    def test_read_value_requires_element(self):
        """read_value 需要 element_name 或 element_type"""
        with patch("tools.accessibility_tool._read_value") as mock:
            mock.return_value = {"error": "需要指定 element_name 或 element_type"}
            result = self._run(accessibility_tool.handler({
                "action": "read_value", "app": "Safari"
            }))
            assert "error" in result


class TestAppleScriptGeneration:
    """测试 AppleScript 生成逻辑（mock subprocess）"""

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch("tools.accessibility_tool._run_applescript")
    def test_list_apps_calls_system_events(self, mock_run):
        mock_run.return_value = {"result": "Safari, Finder, Mail"}
        result = self._run(accessibility_tool.handler({"action": "list_apps"}))
        assert result == {"result": "Safari, Finder, Mail"}
        # 验证调用了 System Events
        call_script = mock_run.call_args[0][0]
        assert "System Events" in call_script
        assert "background only is false" in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_click_button_by_name(self, mock_run):
        mock_run.return_value = {"result": "已点击: 提交"}
        result = self._run(accessibility_tool.handler({
            "action": "click",
            "app": "Safari",
            "element_type": "button",
            "element_name": "提交",
        }))
        assert result == {"result": "已点击: 提交"}
        call_script = mock_run.call_args[0][0]
        assert 'click button "提交"' in call_script
        assert 'process "Safari"' in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_type_text_with_app(self, mock_run):
        mock_run.return_value = {"result": "执行成功"}
        result = self._run(accessibility_tool.handler({
            "action": "type_text",
            "app": "Safari",
            "text": "hello world",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert 'keystroke "hello world"' in call_script
        assert '"Safari" to activate' in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_key_press_with_modifiers(self, mock_run):
        mock_run.return_value = {"result": "执行成功"}
        result = self._run(accessibility_tool.handler({
            "action": "key_press",
            "keys": "command+shift+n",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert "command down" in call_script
        assert "shift down" in call_script
        assert 'keystroke "n"' in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_key_press_special_key(self, mock_run):
        mock_run.return_value = {"result": "执行成功"}
        result = self._run(accessibility_tool.handler({
            "action": "key_press",
            "keys": "return",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert "key code 36" in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_menu_click_two_levels(self, mock_run):
        mock_run.return_value = {"result": "执行成功"}
        result = self._run(accessibility_tool.handler({
            "action": "menu_click",
            "app": "Finder",
            "menu_path": "文件,新建 Finder 窗口",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert 'menu item "新建 Finder 窗口"' in call_script
        assert 'menu "文件"' in call_script

    def test_menu_click_single_level_error(self):
        """菜单路径至少需要两级"""
        result = self._run(accessibility_tool.handler({
            "action": "menu_click",
            "app": "Finder",
            "menu_path": "文件",
        }))
        assert "error" in result
        assert "两级" in result["error"]

    @patch("tools.accessibility_tool._run_applescript")
    def test_list_elements_all_types(self, mock_run):
        mock_run.return_value = {"result": 'button: 提交\ntext field: 搜索'}
        result = self._run(accessibility_tool.handler({
            "action": "list_elements",
            "app": "Safari",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert "every UI element" in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_list_elements_specific_type(self, mock_run):
        mock_run.return_value = {"result": "提交 | \n取消 | "}
        result = self._run(accessibility_tool.handler({
            "action": "list_elements",
            "app": "Safari",
            "element_type": "button",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert "every button" in call_script

    @patch("tools.accessibility_tool._run_applescript")
    def test_set_value_by_name(self, mock_run):
        mock_run.return_value = {"result": "执行成功"}
        result = self._run(accessibility_tool.handler({
            "action": "set_value",
            "app": "Safari",
            "element_name": "搜索",
            "text": "周杰伦",
        }))
        assert "result" in result
        call_script = mock_run.call_args[0][0]
        assert 'text field "搜索"' in call_script
        assert '"周杰伦"' in call_script


class TestRunAppleScript:
    """测试 _run_applescript 辅助函数"""

    @patch("subprocess.run")
    def test_success(self, mock_subprocess):
        mock_subprocess.return_value = type("Result", (), {
            "stdout": "ok\n", "stderr": "", "returncode": 0
        })()
        result = _run_applescript('tell application "Finder" to activate')
        assert result == {"result": "ok"}

    @patch("subprocess.run")
    def test_error(self, mock_subprocess):
        mock_subprocess.return_value = type("Result", (), {
            "stdout": "", "stderr": "execution error", "returncode": 1
        })()
        result = _run_applescript("bad script")
        assert "error" in result

    @patch("subprocess.run", side_effect=Exception("osascript not found"))
    def test_exception(self, mock_subprocess):
        result = _run_applescript("any script")
        assert "error" in result
        assert "osascript" in result["error"]
