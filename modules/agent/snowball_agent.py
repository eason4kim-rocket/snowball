"""雪球 Agent — 基于 open-agent-sdk-python"""

from __future__ import annotations

import os
from pathlib import Path

from open_agent_sdk import AgentOptions, create_agent
from open_agent_sdk import Agent as SDKAgent

from .base import AgentBase
from .system_prompt import SNOWBALL_SYSTEM_PROMPT


class SnowballAgent(AgentBase):
    """雪球的 Agent 实现，封装 open-agent-sdk"""

    def __init__(
        self,
        api_type: str = "openai-completions",
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3:8b",
        max_turns: int = 10,
        memory_path: str = "SNOWBALL.md",
        tools: list | None = None,
    ):
        self._api_type = api_type
        self._base_url = base_url
        self._model = model
        self._max_turns = max_turns
        self._memory_path = Path(memory_path)
        self._custom_tools = tools or []
        self._agent: SDKAgent | None = None

    def _build_system_prompt(self) -> str:
        """构建系统提示词：人格 + 记忆"""
        prompt = SNOWBALL_SYSTEM_PROMPT

        # 注入记忆
        if self._memory_path.exists():
            memory_content = self._memory_path.read_text(encoding="utf-8")
            prompt += f"\n\n## 当前记忆\n{memory_content}"

        return prompt

    async def _ensure_agent(self) -> SDKAgent:
        """懒初始化 SDK Agent"""
        if self._agent is not None:
            return self._agent

        system_prompt = self._build_system_prompt()

        options = AgentOptions(
            api_type=self._api_type,
            base_url=self._base_url,
            model=self._model,
            max_turns=self._max_turns,
            system_prompt=system_prompt,
            permission_mode="bypassPermissions",
            tools=self._custom_tools,
        )

        self._agent = create_agent(options)
        return self._agent

    async def chat(self, text: str) -> str:
        """接收文字输入，返回文字回复"""
        agent = await self._ensure_agent()
        result = await agent.prompt(text)
        return result.text or ""

    async def close(self) -> None:
        """释放资源"""
        if self._agent:
            await self._agent.close()
            self._agent = None
