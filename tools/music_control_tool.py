"""音乐控制工具 - 通过 System Events 控制 AlgerMusicPlayer"""

import subprocess
import time

from open_agent import tool

from ._mouse import click_at
from .retry import with_retry

_APP_NAME = "AlgerMusicPlayer"


def _is_running() -> bool:
    r = subprocess.run(["pgrep", "-x", _APP_NAME], capture_output=True, text=True)
    return bool(r.stdout.strip())


def _open_with_ax() -> dict:
    """以 --force-renderer-accessibility flag 启动 AlgerMusicPlayer。
    如果已在运行，先 quit 再启动（flag 只在冷启动生效）。"""
    try:
        if _is_running():
            subprocess.run(
                ["osascript", "-e", f'tell application "{_APP_NAME}" to quit'],
                timeout=5,
            )
            # 等它彻底退出
            for _ in range(20):
                if not _is_running():
                    break
                time.sleep(0.15)
        subprocess.run(
            ["open", "-a", _APP_NAME, "--args", "--force-renderer-accessibility"],
            check=True, timeout=5,
        )
        # 等窗口可用
        time.sleep(2.5)
        return {"result": f"已打开 {_APP_NAME}（含 AX flag）"}
    except Exception as e:
        return {"error": str(e)}


def _run_applescript(script: str, timeout: int = 10) -> dict:
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout.strip() if result.stdout else result.stderr.strip()
        if result.returncode != 0 and result.stderr:
            return {"error": result.stderr.strip()}
        return {"result": output or "执行成功"}
    except subprocess.TimeoutExpired:
        return {"error": "AppleScript 执行超时"}
    except Exception as e:
        return {"error": str(e)}


@tool(
    name="MusicControl",
    description=(
        "控制音乐播放器（AlgerMusicPlayer）。"
        "action='open'：以 Accessibility 模式打开播放器；"
        "action='search'：搜索歌手/歌曲并自动播放第一首（需提供 query 参数）；"
        "action='play_pause'：播放/暂停切换（空格键）；"
        "action='next'：下一首；"
        "action='prev'：上一首；"
        "action='volume'：设置系统音量（0-100，需提供 level 参数）"
    ),
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "操作类型：open/search/play_pause/next/prev/volume",
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（歌手名/歌曲名），action=search 时必填",
            },
            "level": {
                "type": "integer",
                "description": "音量 0-100，action=volume 时必填",
            },
        },
        "required": ["action"],
    },
)
@with_retry(max_retries=2, retry_delay=0.5)
async def music_control_tool(args: dict) -> dict:
    action = args.get("action", "")
    query = args.get("query", "")
    level = args.get("level", 50)

    if action == "open":
        return _open_with_ax()

    elif action == "search":
        if not query:
            return {"error": "搜索需要提供 query 参数（歌手名或歌曲名）"}
        safe_query = query.replace("\\", "\\\\").replace('"', '\\"')

        # Step 1: 激活 + 用 AX 设置搜索框 value + Enter
        search_script = f'''
tell application "{_APP_NAME}" to activate
delay 0.8
tell application "System Events"
    tell process "{_APP_NAME}"
        set frontmost to true
        set allElements to entire contents of window 1
        set foundField to false
        repeat with e in allElements
            try
                if role of e is "AXTextField" then
                    set value of e to "{safe_query}"
                    set focused of e to true
                    set foundField to true
                    exit repeat
                end if
            end try
        end repeat
        if not foundField then
            return "NO_FIELD"
        end if
    end tell
    delay 0.4
    key code 36
    delay 1.8
    key code 53
end tell
return "OK"'''
        r1 = _run_applescript(search_script, timeout=20)
        # 没 AX 树 → 自动重启带 flag 后重试一次
        if r1.get("result") == "NO_FIELD":
            reopen = _open_with_ax()
            if reopen.get("error"):
                return {"error": f"自动重启失败：{reopen['error']}"}
            r1 = _run_applescript(search_script, timeout=20)
            if r1.get("result") == "NO_FIELD":
                return {"error": "重启后仍找不到搜索框（AX flag 可能没生效）"}
        if r1.get("error"):
            return r1

        # Step 2: 取窗口位置 + 第一张专辑封面（AXImage #2）位置
        #   AXImage #1 通常是 logo，#2 开始是歌曲列表的封面
        locate_script = '''
tell application "System Events"
    tell process "AlgerMusicPlayer"
        set p to position of window 1
        set s to size of window 1
        set allElements to entire contents of window 1
        set n to 0
        set coverPos to {0, 0}
        repeat with e in allElements
            try
                if role of e is "AXImage" then
                    set n to n + 1
                    if n = 2 then
                        set coverPos to position of e
                        exit repeat
                    end if
                end if
            end try
        end repeat
        return "" & (item 1 of p) & "|" & (item 2 of p) & "|" & (item 1 of s) & "|" & (item 2 of s) & "|" & (item 1 of coverPos) & "|" & (item 2 of coverPos)
    end tell
end tell'''
        r2 = _run_applescript(locate_script, timeout=5)
        try:
            nums = list(map(int, r2["result"].split("|")))
            win_x, win_y, win_w, win_h, cover_x, cover_y = nums
        except Exception as e:
            return {"error": f"读取窗口/封面坐标失败：{e}（原值：{r2}）"}

        if cover_x == 0 and cover_y == 0:
            return {
                "result": f"已搜索 {query}，但没找到结果行（可能搜索词不匹配任何歌曲）",
            }

        # Step 3: 点击第一行最右端的 ▶️ 播放按钮
        # 播放按钮在行右边距约 40px 内，行垂直中心 = 封面 y + 封面高度一半
        play_x = win_x + win_w - 40
        play_y = cover_y + 24
        time.sleep(0.2)
        click_at(play_x, play_y)

        return {
            "result": f"已搜索 {query} 并播放第一首结果",
        }

    elif action == "play_pause":
        return _run_applescript(f'''
tell application "{_APP_NAME}" to activate
delay 0.3
tell application "System Events" to keystroke " "''')

    elif action == "next":
        return _run_applescript(f'''
tell application "{_APP_NAME}" to activate
delay 0.3
tell application "System Events" to keystroke (ASCII character 30)''')

    elif action == "prev":
        return _run_applescript(f'''
tell application "{_APP_NAME}" to activate
delay 0.3
tell application "System Events" to keystroke (ASCII character 31)''')

    elif action == "volume":
        level = max(0, min(100, level))
        return _run_applescript(f'set volume output volume {level}')

    else:
        return {"error": f"未知操作：{action}，支持：open/search/play_pause/next/prev/volume"}
