"""雪球 Web Dashboard — FastAPI 后端

启动: uvicorn web.app:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from modules.agent import SnowballAgent
from tools import create_all_tools
from tools.memory_tool import configure_memory_path

app = FastAPI(title="雪球 Snowball Dashboard", version="0.1.0")

# ── 全局状态 ──

_agent: SnowballAgent | None = None
_config: dict = {}
_chat_history: list[dict] = []  # {"role": "user"|"assistant", "content": "..."}


def _load_config() -> dict:
    path = Path("config.yaml")
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _get_agent() -> SnowballAgent:
    global _agent, _config
    if _agent is None:
        _config = _load_config()
        agent_cfg = _config.get("agent", {})
        memory_cfg = _config.get("memory", {})
        memory_path = memory_cfg.get("path", "SNOWBALL.md")
        tools = create_all_tools(memory_path=memory_path)
        _agent = SnowballAgent(
            base_url=agent_cfg.get("base_url", "http://localhost:11434/v1"),
            model=agent_cfg.get("model", "qwen3:8b"),
            max_tool_iterations=agent_cfg.get("max_tool_iterations", 10),
            memory_path=memory_path,
            tools=tools,
        )
    return _agent


# ── API 模型 ──


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class MemoryUpdate(BaseModel):
    content: str


class ConfigUpdate(BaseModel):
    config: dict


# ── 页面 ──


@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# ── REST API ──


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """文字对话（非流式）"""
    agent = _get_agent()
    _chat_history.append({"role": "user", "content": req.message})
    reply = await agent.chat(req.message, verbose=False)
    _chat_history.append({"role": "assistant", "content": reply})
    return ChatResponse(reply=reply)


@app.get("/api/history")
async def get_history():
    """获取对话历史"""
    return {"history": _chat_history}


@app.post("/api/clear")
async def clear_history():
    """清除对话历史"""
    agent = _get_agent()
    await agent.clear_history()
    _chat_history.clear()
    return {"result": "对话已清除"}


@app.get("/api/memory")
async def get_memory():
    """获取记忆文件内容"""
    config = _load_config()
    path = Path(config.get("memory", {}).get("path", "SNOWBALL.md"))
    if path.exists():
        return {"content": path.read_text(encoding="utf-8")}
    return {"content": ""}


@app.put("/api/memory")
async def update_memory(req: MemoryUpdate):
    """更新记忆文件"""
    config = _load_config()
    path = Path(config.get("memory", {}).get("path", "SNOWBALL.md"))
    path.write_text(req.content, encoding="utf-8")
    return {"result": "记忆已更新"}


@app.get("/api/config")
async def get_config():
    """获取配置"""
    return {"config": _load_config()}


@app.put("/api/config")
async def update_config(req: ConfigUpdate):
    """更新配置"""
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(req.config, f, allow_unicode=True, default_flow_style=False)
    # 重置 agent 以应用新配置
    global _agent
    if _agent:
        await _agent.close()
        _agent = None
    return {"result": "配置已更新，Agent 已重置"}


# ── WebSocket（流式对话） ──


@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """WebSocket 流式对话：每句话实时推送"""
    await websocket.accept()
    agent = _get_agent()

    try:
        while True:
            data = await websocket.receive_text()
            _chat_history.append({"role": "user", "content": data})

            full_reply = []
            async for sentence in agent.chat_stream(data, verbose=False):
                await websocket.send_json({"type": "sentence", "content": sentence})
                full_reply.append(sentence)

            reply = "".join(full_reply)
            _chat_history.append({"role": "assistant", "content": reply})
            await websocket.send_json({"type": "done", "content": reply})

    except WebSocketDisconnect:
        pass


# ── 启动/关闭 ──


@app.on_event("shutdown")
async def shutdown():
    global _agent
    if _agent:
        await _agent.close()
        _agent = None
