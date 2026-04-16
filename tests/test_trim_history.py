"""对话历史修剪测试 — 验证切分不会破坏 tool_use/tool_result 配对"""

from types import SimpleNamespace

from modules.agent.snowball_agent import SnowballAgent


def _make_agent(max_turns: int = 2) -> SnowballAgent:
    """构造一个 agent（不调用 _ensure_client，避免触发网络）"""
    agent = SnowballAgent.__new__(SnowballAgent)
    agent._max_history_turns = max_turns
    return agent


def _fake_client(history: list[dict]):
    """伪造 open-agent Client 对象，只暴露 message_history 属性"""
    return SimpleNamespace(message_history=history)


class TestTrimHistory:
    def test_short_history_not_trimmed(self):
        agent = _make_agent(max_turns=5)
        history = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        client = _fake_client(history.copy())
        agent._trim_history(client)
        assert client.message_history == history

    def test_trim_on_user_boundary(self):
        """切分点必须落在 role=user 上"""
        agent = _make_agent(max_turns=1)  # max_messages = 3
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
            {"role": "user", "content": "q3"},
            {"role": "assistant", "content": "a3"},
        ]
        client = _fake_client(history)
        agent._trim_history(client)
        # 切完第一条必须是 user
        assert client.message_history[0]["role"] == "user"
        # 且至少保留最近一轮
        assert client.message_history[-1]["content"] == "a3"

    def test_trim_preserves_tool_pairing(self):
        """tool_use 和 tool_result 不能被拆散"""
        agent = _make_agent(max_turns=1)
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "tool_use_1"},
            {"role": "tool", "content": "tool_result_1"},  # 关键：不应被孤立保留
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "q2"},
            {"role": "assistant", "content": "a2"},
        ]
        client = _fake_client(history)
        agent._trim_history(client)
        # 结果的第一条必须是 user，不能是孤立的 tool 或 assistant
        assert client.message_history[0]["role"] == "user"

    def test_fallback_keeps_history_when_no_user(self):
        """兜底：找不到 user 边界就不切"""
        agent = _make_agent(max_turns=1)
        history = [
            {"role": "assistant", "content": "a"},
            {"role": "tool", "content": "t"},
            {"role": "assistant", "content": "b"},
            {"role": "tool", "content": "t2"},
        ]
        client = _fake_client(history.copy())
        agent._trim_history(client)
        # 没 user 就保持原样
        assert client.message_history == history
