"""音乐控制工具 - 通过 System Events 控制 AlgerMusicPlayer"""

import subprocess

from open_agent import tool

_APP_NAME = "AlgerMusicPlayer"


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
        "action='open'：打开播放器；"
        "action='search'：搜索歌手/歌曲并播放（需提供 query 参数）；"
        "action='play_pause'：播放/暂停切换；"
        "action='next'：下一首；"
        "action='prev'：上一首；"
        "action='volume'：设置音量（0-100，需提供 level 参数）"
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
async def music_control_tool(args: dict) -> dict:
    action = args.get("action", "")
    query = args.get("query", "")
    level = args.get("level", 50)

    if action == "open":
        return _run_applescript(f'tell application "{_APP_NAME}" to activate')

    elif action == "search":
        if not query:
            return {"error": "搜索需要提供 query 参数"}
        script = f'''
tell application "{_APP_NAME}" to activate
delay 0.5
tell application "System Events"
    keystroke "f" using command down
    delay 0.5
    keystroke "{query}"
    delay 0.3
    key code 36
end tell'''
        return _run_applescript(script, timeout=15)

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
