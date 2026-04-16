"""雪球 Agent — 基于 open-agent-sdk-python (PyPI: open-agent-sdk, import: open_agent)"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from pathlib import Path

from open_agent import Client, AgentOptions, HOOK_PRE_TOOL_USE, HookDecision, PreToolUseEvent
from open_agent.types import TextBlock, ToolUseBlock, ToolResultBlock

from .base import AgentBase
from .system_prompt import SNOWBALL_SYSTEM_PROMPT
from tools.safety import SafetyGuard

# 中英文句子结束符
_SENTENCE_END_RE = re.compile(r'[。！？、.!?;\n]')


class SnowballAgent(AgentBase):
    """雪球的 Agent 实现，封装 open-agent-sdk"""

    # 每条消息大约占 200-500 token，qwen3.5:9b 上下文窗口 262144
    DEFAULT_MAX_HISTORY_TURNS: int = 20

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3.5:9b",
        max_tool_iterations: int = 10,
        memory_path: str = "SNOWBALL.md",
        tools: list | None = None,
        max_history_turns: int | None = None,
    ):
        self._base_url = base_url
        self._model = model
        self._max_tool_iterations = max_tool_iterations
        self._memory_path = Path(memory_path)
        self._custom_tools = tools or []
        self._max_history_turns = max_history_turns or self.DEFAULT_MAX_HISTORY_TURNS
        self._client: Client | None = None
        self._last_memory_hash: int = 0  # 用于检测记忆变更，避免无变化时重建 prompt
        self._safety_guard = SafetyGuard(enabled=True)

    def _build_system_prompt(self) -> str:
        """构建系统提示词：人格 + 记忆"""
        prompt = SNOWBALL_SYSTEM_PROMPT

        # 注入记忆
        if self._memory_path.exists():
            memory_content = self._memory_path.read_text(encoding="utf-8")
            prompt += f"\n\n## 当前记忆\n{memory_content}"

        return prompt

    async def _ensure_client(self) -> Client:
        """懒初始化 Client"""
        if self._client is not None:
            return self._client

        system_prompt = self._build_system_prompt()

        options = AgentOptions(
            system_prompt=system_prompt,
            model=self._model,
            base_url=self._base_url,
            tools=self._custom_tools,
            auto_execute_tools=True,
            max_tool_iterations=self._max_tool_iterations,
            api_key="not-needed",
        )

        self._client = Client(options)

        # 注册安全检查钩子
        guard = self._safety_guard

        async def _safety_hook(event: PreToolUseEvent) -> HookDecision | None:
            if guard.needs_confirmation(event.tool_name, event.tool_input):
                risk = guard.describe_risk(event.tool_name, event.tool_input)
                allowed = await guard.confirm(event.tool_name, event.tool_input)
                if not allowed:
                    return HookDecision(
                        continue_=False,
                        reason=f"用户拒绝执行: {risk}",
                    )
            return None

        self._client.options.hooks = {HOOK_PRE_TOOL_USE: [_safety_hook]}

        return self._client

    def _refresh_memory_if_changed(self, client: Client) -> None:
        """仅在记忆文件有变更时刷新系统提示词（减少无变化时的开销）"""
        if self._memory_path.exists():
            memory = self._memory_path.read_text(encoding="utf-8")
            memory_hash = hash(memory)
        else:
            memory = ""
            memory_hash = 0

        if memory_hash != self._last_memory_hash:
            if memory:
                client.options.system_prompt = SNOWBALL_SYSTEM_PROMPT + f"\n\n## 当前记忆\n{memory}"
            else:
                client.options.system_prompt = SNOWBALL_SYSTEM_PROMPT
            self._last_memory_hash = memory_hash

    def _trim_history(self, client: Client) -> None:
        """修剪对话历史，保留最近 N 轮（避免 token 溢出）。

        切分必须在 user 消息边界进行，否则会把 tool_use 和 tool_result
        拆散（LLM 会报 tool_use_id mismatch）。
        """
        history = client.message_history
        # 每轮对话含 user + assistant 两条，可能再加若干 tool_use/tool_result
        max_messages = self._max_history_turns * 3  # 宽松估计
        if len(history) <= max_messages:
            return

        # 从末尾往前数 max_messages 条，然后向后找到第一个 role=user 的位置
        # 从该位置开始切，保证 tool_use/tool_result 配对不被破坏
        start = len(history) - max_messages
        for i in range(start, len(history)):
            msg = history[i]
            role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
            if role == "user":
                client.message_history = history[i:]
                return
        # 兜底：找不到 user 边界就保留全部（宁可不切也不要切坏）

    async def clear_history(self) -> None:
        """清除对话历史（/clear 命令调用）"""
        if self._client:
            self._client.message_history.clear()
            self._client.turn_count = 0

    async def chat(self, text: str, verbose: bool = True) -> str:
        """接收文字输入，返回文字回复（自动维护多轮对话上下文）"""
        response_parts = []
        async for sentence in self.chat_stream(text, verbose=verbose):
            response_parts.append(sentence)
        return "".join(response_parts) if response_parts else "（无回复）"

    async def chat_stream(
        self, text: str, verbose: bool = True
    ) -> AsyncGenerator[str, None]:
        """流式对话：每生成一句完整的话就立即 yield，用于边想边说。"""
        client = await self._ensure_client()

        # 每次对话前刷新记忆（仅在文件变更时重建 prompt）
        self._refresh_memory_if_changed(client)

        # 修剪过长的对话历史，避免 token 溢出
        self._trim_history(client)

        # 发送查询
        await client.query(text)

        # 流式收集回复，按句子切分
        buffer = ""
        async for block in client.receive_messages():
            if isinstance(block, TextBlock):
                if verbose:
                    print(block.text, end="", flush=True)
                buffer += block.text

                # 检查 buffer 中是否有完整句子
                while True:
                    match = _SENTENCE_END_RE.search(buffer)
                    if not match:
                        break
                    # 截取到句子结束符位置
                    end = match.end()
                    sentence = buffer[:end].strip()
                    buffer = buffer[end:]
                    if sentence:
                        yield sentence

            elif isinstance(block, ToolUseBlock):
                if verbose:
                    print(f"\n  🔧 {block.name}...", end="", flush=True)
            elif isinstance(block, ToolResultBlock):
                if verbose:
                    print(" ✓", end="", flush=True)

        # 输出剩余内容
        remaining = buffer.strip()
        if remaining:
            yield remaining

        if verbose:
            print()  # 换行

    async def close(self) -> None:
        """释放资源"""
        if self._client:
            await self._client.close()
            self._client = None
