# Testing Snowball Dashboard

## Overview
Snowball is a local AI voice assistant (Jarvis-style) for macOS. The Web Dashboard (FastAPI + single-page HTML) provides config management, memory editing, and chat. Testing on Linux covers Dashboard UI, API, pytest suite, but NOT voice/STT/TTS/Accessibility (macOS-only).

## Prerequisites
- Python 3.12+ with `pytest`, `httpx`, `fastapi`, `uvicorn` installed
- No secrets needed (all local testing)
- No Ollama needed for config/memory/pytest tests (only needed for chat)

## Running Tests

### 1. Pytest Suite
```bash
cd /home/ubuntu/snowball
python -m pytest tests/ -v --tb=short
```
- Expected: All tests pass (currently 81)
- Key test files: `test_config.py` (config loading + model assertion), `test_e2e_linux.py` (main.py startup), `test_accessibility.py`, `test_memory_tool.py`, `test_safety.py`, `test_retry.py`, `test_wake_word.py`, `test_voice_out.py`, `test_tools_init.py`

### 2. Start Web Dashboard
```bash
fuser -k 8000/tcp 2>/dev/null  # kill any existing server
uvicorn web.app:app --port 8000 --host 0.0.0.0
```
- Dashboard loads at http://localhost:8000
- WebSocket chat will show "已断开" (disconnected) — this is expected without Ollama

### 3. Verify Config Panel
- Click ⚙️ 配置 tab in sidebar
- Textarea should show JSON with current `agent.model` value and `fazm.enabled: false`
- Bottom status shows "已加载" after load, "已保存" after save

### 4. Verify API Endpoint
```bash
curl -s http://localhost:8000/api/config | python3 -m json.tool
```
- Check `config.agent.model` matches expected value

### 5. Memory Panel Regression
- Click 🧠 记忆 tab
- Add test text at end of textarea
- Click 保存 → status shows "已保存"
- Click 刷新 → text persists
- Clean up: remove test text from SNOWBALL.md after testing

## What CAN'T Be Tested on Linux
- Voice input (RealtimeSTT + microphone)
- Voice output playback (macOS `say`/`afplay` commands)
- AccessibilityControl actual GUI ops (macOS `osascript`)
- Ollama LLM chat + tool calling (needs `ollama serve` + model pulled)
- These are tested via mock/unit tests in pytest, but real e2e requires macOS

## Common Issues
- WebSocket warning "No supported WebSocket library detected" — install `websockets` or use `pip install 'uvicorn[standard]'` if you need to test chat
- Dashboard shows "已断开，3 秒后重连" — normal without Ollama backend
- Edge TTS tests may be slow (network calls to Microsoft API) — they generate real mp3 files

## Config Model Changes
When changing the default LLM model, update ALL of these:
1. `config.yaml` — source of truth
2. `main.py` — fallback default in `agent_cfg.get("model", "...")`
3. `modules/agent/snowball_agent.py` — default parameter + comment
4. `web/app.py` — fallback default
5. `README.md` — 4 references (architecture, prerequisites, install command, config example)
6. `ROADMAP.md` — 2 references
7. `tests/test_config.py` — assertion value
8. `tests/test_e2e_linux.py` — assertion value

## Devin Secrets Needed
None — all testing is local without authentication.
