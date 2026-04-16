"""雪球 Agent — 基于 open-agent-sdk-python (PyPI: open-agent-sdk, import: open_agent)"""

from __future__ import annotations

from pathlib import Path

from open_agent import Client, AgentOptions
from open_agent.types import TextBlock, ToolUseBlock, ToolResultBlock

from .base import AgentBase
from .system_prompt import SNOWBALL_SYSTEM_PROMPT


class SnowballAgent(AgentBase):
    """雪球的 Agent 实现，封装 open-agent-sdk"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3:8b",
        max_tool_iterations: int = 10,
        memory_path: str = "SNOWBALL.md",
        tools: list | None = None,
    ):
        self._base_url = base_url
        self._model = model
        self._max_tool_iterations = max_tool_iterations
        self._memory_path = Path(memory_path)
        self._custom_tools = tools or []
        self._client: Client | None = None
        self._last_memory_hash: int = 0  # 用于检测记忆变更，避免无变化时重建 prompt

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

    async def chat(self, text: str, verbose: bool = True) -> str:
        """接收文字输入，返回文字回复"""
        client = await self._ensure_client()

        # 每次对话前刷新记忆（仅在文件变更时重建 prompt）
        self._refresh_memory_if_changed(client)

        # 发送查询
        await client.query(text)

        # 收集所有回复
        response_parts = []
        async for block in client.receive_messages():
            if isinstance(block, TextBlock):
                if verbose:
                    print(block.text, end="", flush=True)
                response_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                if verbose:
                    print(f"\n  🔧 {block.name}...", end="", flush=True)
            elif isinstance(block, ToolResultBlock):
                if verbose:
                    print(" ✓", end="", flush=True)

        if verbose:
            print()  # 换行

        return "".join(response_parts) if response_parts else "（无回复）"

    async def close(self) -> None:
        """释放资源"""
        if self._client:
            await self._client.close()
            self._client = None
