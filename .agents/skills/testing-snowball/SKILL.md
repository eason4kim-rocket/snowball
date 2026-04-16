# Testing Snowball Web Dashboard & Tools

## Overview
Snowball is a local AI assistant running on macOS with a FastAPI Web Dashboard. Testing is split between:
- **Linux-testable**: Dashboard UI, REST API, pytest suite, tool registration
- **macOS-only**: AccessibilityControl GUI operations (osascript), voice input/output, Ollama LLM integration

## Prerequisites
- Python 3.12+ with dependencies installed (`pip install -e .` or `pip install fastapi uvicorn pyyaml edge-tts open-agent-sdk pytest`)
- No Ollama or macOS-specific tools needed for Dashboard/pytest testing

## Starting the Web Dashboard

```bash
# Kill any existing process on port 8000 first
fuser -k 8000/tcp 2>/dev/null; sleep 1

# Start the Dashboard (run from project root)
cd /path/to/snowball
uvicorn web.app:app --port 8000 --host 0.0.0.0
```

**Note**: The WebSocket endpoint (`/ws/chat`) requires the `websockets` pip package. If not installed, REST API and HTML serving still work but the chat panel will show "已断开" (disconnected). This is expected in minimal test environments.

## Key Test Areas

### 1. Config Panel Verification
- Navigate to Dashboard → click "⚙️ 配置" in sidebar
- Verify the config textarea shows correct `model` value and `fazm.enabled` status
- Can also verify via API: `curl -s http://localhost:8000/api/config | python3 -m json.tool`

### 2. Memory Panel Save/Refresh Roundtrip
- Click "🧠 记忆" → verify content loads from SNOWBALL.md
- Edit textarea → click "保存" → verify status shows "已保存"
- Verify file on disk: `grep "<your test text>" SNOWBALL.md`
- Click "刷新" → verify status shows "已加载" and content persists
- **Important**: Clean up test data after testing with `git checkout -- SNOWBALL.md`

### 3. Tool Registration
```bash
python -c "
from tools import create_all_tools
tools = create_all_tools()
print(f'Total tools: {len(tools)}')
for t in tools:
    print(f'  - {t.name}')
"
```
Expected: 7 tools (AccessibilityControl, AppleScript, MacControl, MusicControl, ReadMemory, SearchMemory, WriteMemory). FazmControl should NOT be in the list.

### 4. Pytest Suite
```bash
python -m pytest tests/ -v
```
Expected: 81 tests pass. Key test files:
- `test_accessibility.py` — 22 tests (parameter routing, AppleScript generation, error handling)
- `test_e2e_linux.py` — Edge TTS, memory lifecycle, agent memory refresh, main.py startup
- `test_safety.py` — SafetyGuard dangerous operation detection
- `test_tools_init.py` — Tool count and registration
- `test_config.py` — Config loading and values

## Common Issues

- **Port 8000 already in use**: Run `fuser -k 8000/tcp` to kill the previous process. `lsof` might not be available on some Linux environments.
- **WebSocket disconnected**: Install `websockets` package or use `pip install 'uvicorn[standard]'`. Not required for config/memory panel testing.
- **Stale config in Dashboard**: If the Dashboard was running from a previous session with old config, kill the process and restart. The config is loaded fresh from `config.yaml` on each `/api/config` request.
- **osascript not found**: Expected on Linux. All AccessibilityControl tests use mocks. Real GUI testing requires macOS.

## macOS-Only Testing (User Must Verify)

1. `ollama pull qwen3:14b` — download the model
2. System Settings → Privacy & Security → Accessibility → enable Terminal/Python
3. `python main.py --tts` — test voice mode with streaming TTS
4. Try GUI commands: "列出运行中的应用", "帮我在 Finder 点击菜单 文件→新建窗口"

## Devin Secrets Needed
None — all testing is local with no external API keys required.
