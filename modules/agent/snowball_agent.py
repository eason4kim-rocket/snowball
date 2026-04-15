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

    async def chat(self, text: str) -> str:
        """接收文字输入，返回文字回复"""
        client = await self._ensure_client()

        # 发送查询
        await client.query(text)

        # 收集所有回复
        response_parts = []
        async for block in client.receive_messages():
            if isinstance(block, TextBlock):
                response_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                pass  # 工具调用自动执行
            elif isinstance(block, ToolResultBlock):
                pass  # 工具结果自动处理

        return "\n".join(response_parts) if response_parts else "（无回复）"

    async def close(self) -> None:
        """释放资源"""
        if self._client:
            await self._client.close()
            self._client = None
