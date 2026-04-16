"""Accessibility 工具 — 通过 macOS Accessibility API (System Events) 操控任意 App 的 GUI

替代 Fazm，零外部依赖。底层使用 AppleScript 的 System Events 接口，
实际调用的是 macOS AXUIElement API（无障碍访问接口）。

前提：System Settings → Privacy & Security → Accessibility → 勾选终端 / Python

支持操作：
- list_apps: 列出正在运行的 GUI 应用
- list_elements: 获取某个 App 窗口的 UI 元素树
- click: 点击指定按钮/菜单/元素
- type_text: 在当前焦点输入框中输入文字
- read_value: 读取 UI 元素的值（文本框内容、标签文字等）
- set_value: 设置 UI 元素的值
- key_press: 模拟按键/快捷键
- menu_click: 点击菜单栏菜单项
"""

import subprocess

from open_agent import tool

from .retry import with_retry

# 权限检查缓存（None=未检查，True=已授权，False=无权限）
_AX_PERMISSION_CACHE: bool | None = None

# AppleScript 错误码映射到用户友好描述
_AS_ERROR_CODES = {
    "-1719": (
        "no_ax_permission",
        "当前进程无 Accessibility 权限。"
        "请打开 系统设置 → 隐私与安全 → 辅助功能，"
        "勾选运行雪球的终端或 Windsurf 或 Python。",
    ),
    "-1728": ("element_not_found", "未找到指定的 UI 元素（可能已关闭或名称不对）"),
    "-10810": ("app_not_running", "目标应用未运行"),
    "-50": ("invalid_param", "AppleScript 参数错误（检查 app/element 名称）"),
}


def _check_ax_permission() -> bool:
    """快速检查是否有 Accessibility 权限（结果缓存）"""
    global _AX_PERMISSION_CACHE
    if _AX_PERMISSION_CACHE is not None:
        return _AX_PERMISSION_CACHE

    # 探针：读 Dock 的 UI elements（Dock 一定在跑，且不是调用者自己，
    # 能真正触发跨进程 AX 权限检查）
    probe = (
        'tell application "System Events"\n'
        "    try\n"
        '        set _ to UI elements of process "Dock"\n'
        '        return "ok"\n'
        "    on error errMsg number errNum\n"
        '        return "err:" & errNum\n'
        "    end try\n"
        "end tell"
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", probe],
            capture_output=True, text=True, timeout=3,
        )
        out = (result.stdout or "").strip()
        stderr = (result.stderr or "")
        _AX_PERMISSION_CACHE = (
            out == "ok" and "-1719" not in stderr
        )
    except Exception:
        _AX_PERMISSION_CACHE = False
    return _AX_PERMISSION_CACHE


def _parse_applescript_error(stderr: str) -> dict:
    """从 AppleScript 报错中识别错误码，返回结构化 error"""
    for code, (kind, desc) in _AS_ERROR_CODES.items():
        if code in stderr:
            return {"error": desc, "error_kind": kind, "error_code": code}
    return {"error": stderr.strip()}


def _run_applescript(script: str, timeout: int = 15) -> dict:
    """执行 AppleScript 并返回结果"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stderr = (result.stderr or "").strip()
        if result.returncode != 0 and stderr:
            return _parse_applescript_error(stderr)
        # osascript 有时 returncode=0 但 stderr 仍含权限错误
        if "-1719" in stderr:
            return _parse_applescript_error(stderr)
        return {"result": (result.stdout or "").strip() or "执行成功"}
    except subprocess.TimeoutExpired:
        return {"error": "操作超时", "error_kind": "timeout"}
    except Exception as e:
        return {"error": str(e), "error_kind": "unknown"}


@tool(
    name="AccessibilityControl",
    description=(
        "通过 macOS Accessibility API 操控任意 App 的 GUI 元素。"
        "适用于：点击按钮、填写表单、读取界面文字、操作菜单、模拟快捷键等。"
        "当 AppleScript 无法直接完成某个操作时，用这个工具通过 UI 元素精准控制。\n"
        "action 可选值：\n"
        "- list_apps: 列出运行中的 GUI 应用\n"
        "- list_elements: 获取 App 窗口的 UI 元素（按钮、文本框等）\n"
        "- click: 点击按钮或 UI 元素（需指定 app + element_name 或 element_type）\n"
        "- type_text: 在当前焦点位置输入文字\n"
        "- read_value: 读取某个 UI 元素的值\n"
        "- set_value: 设置文本框等元素的值\n"
        "- key_press: 模拟按键（如 return, tab, command+c）\n"
        "- menu_click: 点击菜单栏菜单项（如 文件 → 新建）\n\n"
        "示例：\n"
        '- 列出 Safari 的按钮: action="list_elements", app="Safari", element_type="button"\n'
        '- 点击按钮: action="click", app="Safari", element_name="提交"\n'
        '- 输入文字: action="type_text", app="Safari", text="hello"\n'
        '- 菜单操作: action="menu_click", app="Finder", menu_path="文件,新建 Finder 窗口"\n'
        '- 快捷键: action="key_press", keys="command+shift+n"'
    ),
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": (
                    "操作类型：list_apps, list_elements, click, "
                    "type_text, read_value, set_value, key_press, menu_click"
                ),
            },
            "app": {
                "type": "string",
                "description": "目标应用名称（如 Safari, Mail, Finder）",
            },
            "element_type": {
                "type": "string",
                "description": (
                    "UI 元素类型：button, text field, checkbox, "
                    "radio button, pop up button, scroll area, "
                    "static text, image, group, toolbar, tab group"
                ),
            },
            "element_name": {
                "type": "string",
                "description": "UI 元素名称/标签（按钮文字、输入框标签等）",
            },
            "text": {
                "type": "string",
                "description": "要输入的文字（type_text / set_value 时使用）",
            },
            "keys": {
                "type": "string",
                "description": "快捷键，如 return, tab, command+c, command+shift+n",
            },
            "menu_path": {
                "type": "string",
                "description": '菜单路径，逗号分隔，如 "文件,新建 Finder 窗口"',
            },
            "window_index": {
                "type": "integer",
                "description": "窗口索引（默认 1 = 最前面的窗口）",
            },
        },
        "required": ["action"],
    },
)
@with_retry(max_retries=2, retry_delay=0.5)
async def accessibility_tool(args: dict) -> dict:
    """通过 Accessibility API 操控 macOS GUI 元素（失败自动重试 2 次）"""
    action = args.get("action", "")
    app = args.get("app", "")
    element_type = args.get("element_type", "")
    element_name = args.get("element_name", "")
    text = args.get("text", "")
    keys = args.get("keys", "")
    menu_path = args.get("menu_path", "")
    window_index = args.get("window_index", 1)

    # list_apps 不需要 AX 权限，其他操作需要先检查
    if action != "list_apps" and not _check_ax_permission():
        return {
            "error": (
                "❌ 当前进程无 Accessibility 权限，无法读取/操控 UI 元素。\n"
                "修复：系统设置 → 隐私与安全 → 辅助功能 → 勾选运行雪球的"
                "终端 / Windsurf / Python（授权后重启雪球生效）。"
            ),
            "error_kind": "no_ax_permission",
        }

    if action == "list_apps":
        return _list_apps()
    elif action == "list_elements":
        if not app:
            return {"error": "需要指定 app 参数"}
        return _list_elements(app, element_type, window_index)
    elif action == "click":
        if not app:
            return {"error": "需要指定 app 参数"}
        return _click_element(app, element_type, element_name, window_index)
    elif action == "type_text":
        if not text:
            return {"error": "需要指定 text 参数"}
        return _type_text(app, text)
    elif action == "read_value":
        if not app:
            return {"error": "需要指定 app 参数"}
        return _read_value(app, element_type, element_name, window_index)
    elif action == "set_value":
        if not app or not text:
            return {"error": "需要指定 app 和 text 参数"}
        return _set_value(app, element_type, element_name, text, window_index)
    elif action == "key_press":
        if not keys:
            return {"error": "需要指定 keys 参数"}
        return _key_press(app, keys)
    elif action == "menu_click":
        if not app or not menu_path:
            return {"error": "需要指定 app 和 menu_path 参数"}
        return _menu_click(app, menu_path)
    else:
        return {"error": f"未知操作：{action}"}


def _list_apps() -> dict:
    """列出运行中的 GUI 应用"""
    script = (
        'tell application "System Events"\n'
        "    set appList to name of every process whose background only is false\n"
        "    set AppleScript's text item delimiters to \", \"\n"
        "    return appList as text\n"
        "end tell"
    )
    return _run_applescript(script)


def _list_elements(app: str, element_type: str, window_index: int) -> dict:
    """获取 App 窗口的 UI 元素列表"""
    # 映射常见中文/简写到 AppleScript UI 元素类型
    type_map = {
        "button": "button",
        "text field": "text field",
        "text_field": "text field",
        "checkbox": "checkbox",
        "radio button": "radio button",
        "radio_button": "radio button",
        "pop up button": "pop up button",
        "popup": "pop up button",
        "static text": "static text",
        "label": "static text",
        "image": "image",
        "group": "group",
        "toolbar": "toolbar",
        "tab group": "tab group",
        "scroll area": "scroll area",
        "table": "table",
        "menu button": "menu button",
        "slider": "slider",
    }
    ax_type = type_map.get(element_type.lower(), element_type) if element_type else ""

    if ax_type:
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f"        set elems to every {ax_type} of window {window_index}\n"
            f"        set infoList to {{}}\n"
            f"        repeat with e in elems\n"
            f'            set end of infoList to (name of e & " | " & description of e)\n'
            f"        end repeat\n"
            f"        set AppleScript's text item delimiters to \"\\n\"\n"
            f"        return infoList as text\n"
            f"    end tell\n"
            f"end tell"
        )
    else:
        # 列出所有 UI 元素的概要
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f"        set elems to every UI element of window {window_index}\n"
            f"        set infoList to {{}}\n"
            f"        repeat with e in elems\n"
            f'            set end of infoList to (class of e as text) & ": " & (name of e as text)\n'
            f"        end repeat\n"
            f"        set AppleScript's text item delimiters to \"\\n\"\n"
            f"        return infoList as text\n"
            f"    end tell\n"
            f"end tell"
        )
    return _run_applescript(script)


def _click_element(app: str, element_type: str, element_name: str, window_index: int) -> dict:
    """点击 UI 元素"""
    if element_name and element_type:
        # 按类型 + 名称精准点击
        type_map = {
            "button": "button",
            "checkbox": "checkbox",
            "radio button": "radio button",
            "pop up button": "pop up button",
            "menu button": "menu button",
        }
        ax_type = type_map.get(element_type.lower(), element_type)
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f'        click {ax_type} "{element_name}" of window {window_index}\n'
            f"    end tell\n"
            f"end tell"
        )
    elif element_name:
        # 按名称递归查找（entire contents 返回所有嵌套元素）
        # 模糊匹配：name / title / description / help 任一包含即匹配
        escaped_name = element_name.replace("\\", "\\\\").replace('"', '\\"')
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f"        set targetWindow to window {window_index}\n"
            f"        set allElements to entire contents of targetWindow\n"
            f"        repeat with e in allElements\n"
            f"            try\n"
            f'                set elemName to (name of e as text)\n'
            f'                if elemName contains "{escaped_name}" then\n'
            f"                    click e\n"
            f'                    return "已点击: " & elemName\n'
            f"                end if\n"
            f"            end try\n"
            f"            try\n"
            f'                set elemDesc to (description of e as text)\n'
            f'                if elemDesc contains "{escaped_name}" then\n'
            f"                    click e\n"
            f'                    return "已点击(按描述): " & elemDesc\n'
            f"                end if\n"
            f"            end try\n"
            f"        end repeat\n"
            f'        return "未找到元素: {escaped_name}"\n'
            f"    end tell\n"
            f"end tell"
        )
    else:
        return {"error": "需要指定 element_name 或同时指定 element_type + element_name"}

    return _run_applescript(script)


def _type_text(app: str, text: str) -> dict:
    """在当前焦点位置输入文字"""
    # 转义特殊字符
    escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')

    if app:
        script = (
            f'tell application "{app}" to activate\n'
            f"delay 0.3\n"
            f'tell application "System Events"\n'
            f'    keystroke "{escaped_text}"\n'
            f"end tell"
        )
    else:
        script = (
            f'tell application "System Events"\n'
            f'    keystroke "{escaped_text}"\n'
            f"end tell"
        )
    return _run_applescript(script)


def _read_value(app: str, element_type: str, element_name: str, window_index: int) -> dict:
    """读取 UI 元素的值"""
    if element_name and element_type:
        type_map = {
            "text field": "text field",
            "text_field": "text field",
            "static text": "static text",
            "label": "static text",
            "checkbox": "checkbox",
            "pop up button": "pop up button",
        }
        ax_type = type_map.get(element_type.lower(), element_type)
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f'        return value of {ax_type} "{element_name}" of window {window_index}\n'
            f"    end tell\n"
            f"end tell"
        )
    elif element_name:
        escaped_name = element_name.replace("\\", "\\\\").replace('"', '\\"')
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f"        set allElements to entire contents of window {window_index}\n"
            f"        repeat with e in allElements\n"
            f"            try\n"
            f'                if (name of e as text) contains "{escaped_name}" then\n'
            f"                    return value of e\n"
            f"                end if\n"
            f"            end try\n"
            f"        end repeat\n"
            f'        return "未找到元素: {escaped_name}"\n'
            f"    end tell\n"
            f"end tell"
        )
    elif element_type:
        # 读取第一个该类型元素的值
        type_map = {
            "text field": "text field",
            "text_field": "text field",
            "static text": "static text",
        }
        ax_type = type_map.get(element_type.lower(), element_type)
        script = (
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f"        return value of {ax_type} 1 of window {window_index}\n"
            f"    end tell\n"
            f"end tell"
        )
    else:
        return {"error": "需要指定 element_name 或 element_type"}

    return _run_applescript(script)


def _set_value(app: str, element_type: str, element_name: str, text: str, window_index: int) -> dict:
    """设置 UI 元素的值"""
    escaped_text = text.replace("\\", "\\\\").replace('"', '\\"')

    if element_name:
        type_str = f'text field "{element_name}"'
    elif element_type:
        type_map = {"text field": "text field", "text_field": "text field"}
        ax_type = type_map.get(element_type.lower(), element_type)
        type_str = f"{ax_type} 1"
    else:
        return {"error": "需要指定 element_name 或 element_type"}

    script = (
        f'tell application "System Events"\n'
        f'    tell process "{app}"\n'
        f'        set value of {type_str} of window {window_index} to "{escaped_text}"\n'
        f"    end tell\n"
        f"end tell"
    )
    return _run_applescript(script)


def _key_press(app: str, keys: str) -> dict:
    """模拟按键/快捷键"""
    # 解析快捷键格式: command+shift+n → keystroke "n" using {command down, shift down}
    parts = [k.strip().lower() for k in keys.split("+")]

    modifier_map = {
        "command": "command down",
        "cmd": "command down",
        "shift": "shift down",
        "option": "option down",
        "alt": "option down",
        "control": "control down",
        "ctrl": "control down",
    }

    # 特殊键映射
    special_keys = {
        "return": "return",
        "enter": "return",
        "tab": "tab",
        "escape": "escape",
        "esc": "escape",
        "space": "space",
        "delete": "delete",
        "backspace": "delete",
        "left": "left arrow",
        "right": "right arrow",
        "up": "up arrow",
        "down": "down arrow",
    }

    modifiers = []
    key_char = ""

    for part in parts:
        if part in modifier_map:
            modifiers.append(modifier_map[part])
        elif part in special_keys:
            key_char = special_keys[part]
        else:
            key_char = part

    # 构建 keystroke 命令
    if key_char in special_keys.values():
        # 特殊键用 key code 的方式不太方便，用 keystroke 替代
        key_code_map = {
            "return": 36, "tab": 48, "escape": 53, "space": 49,
            "delete": 51, "left arrow": 123, "right arrow": 124,
            "up arrow": 126, "down arrow": 125,
        }
        if key_char not in key_code_map:
            return {
                "error": f"不支持的特殊键: {key_char}",
                "error_kind": "invalid_key",
            }
        code = key_code_map[key_char]
        if modifiers:
            modifier_str = "{" + ", ".join(modifiers) + "}"
            keystroke = f"key code {code} using {modifier_str}"
        else:
            keystroke = f"key code {code}"
    else:
        if modifiers:
            modifier_str = "{" + ", ".join(modifiers) + "}"
            keystroke = f'keystroke "{key_char}" using {modifier_str}'
        else:
            keystroke = f'keystroke "{key_char}"'

    if app:
        script = (
            f'tell application "{app}" to activate\n'
            f"delay 0.2\n"
            f'tell application "System Events"\n'
            f"    {keystroke}\n"
            f"end tell"
        )
    else:
        script = (
            f'tell application "System Events"\n'
            f"    {keystroke}\n"
            f"end tell"
        )
    return _run_applescript(script)


def _menu_click(app: str, menu_path: str) -> dict:
    """点击菜单栏菜单项"""
    items = [item.strip() for item in menu_path.split(",")]

    if len(items) < 2:
        return {"error": '菜单路径至少需要两级，如 "文件,新建"'}

    # 构建嵌套的菜单点击
    # 例: "文件,新建 Finder 窗口" →
    #   click menu item "新建 Finder 窗口" of menu "文件" of menu bar 1
    menu_name = items[0]

    if len(items) == 2:
        menu_item = items[1]
        script = (
            f'tell application "{app}" to activate\n'
            f"delay 0.3\n"
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f'        click menu item "{menu_item}" of menu "{menu_name}" of menu bar item "{menu_name}" of menu bar 1\n'
            f"    end tell\n"
            f"end tell"
        )
    elif len(items) == 3:
        submenu = items[1]
        menu_item = items[2]
        script = (
            f'tell application "{app}" to activate\n'
            f"delay 0.3\n"
            f'tell application "System Events"\n'
            f'    tell process "{app}"\n'
            f'        click menu item "{menu_item}" of menu "{submenu}" of menu item "{submenu}" of menu "{menu_name}" of menu bar item "{menu_name}" of menu bar 1\n'
            f"    end tell\n"
            f"end tell"
        )
    else:
        return {"error": "目前最多支持三级菜单"}

    return _run_applescript(script)
