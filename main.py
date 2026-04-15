"""雪球（Snowball）— 你的本地 AI 助手

Phase 1：终端文字交互模式
"""

import asyncio
import sys
from pathlib import Path

import yaml

from modules.agent import SnowballAgent
from tools import create_all_tools


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def print_banner():
    """打印启动横幅"""
    print("""
  ╔══════════════════════════════════════╗
  ║    ❄️  雪球 Snowball v0.1.0          ║
  ║    你的本地 AI 助手                   ║
  ║    输入命令，输入 /quit 退出          ║
  ╚══════════════════════════════════════╝
    """)


async def text_mode(agent: SnowballAgent):
    """终端文字交互模式"""
    print_banner()
    print("雪球已就绪，老大请说 👊\n")

    while True:
        try:
            user_input = input("老大 > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见老大！")
            break

        if not user_input:
            continue

        if user_input in ("/quit", "/exit", "/q"):
            print("再见老大！")
            break

        if user_input == "/help":
            print("  /quit  - 退出")
            print("  /help  - 帮助")
            print("  /clear - 清除对话")
            continue

        if user_input == "/clear":
            # TODO: reset agent history
            print("对话已清除")
            continue

        # 发送给 Agent
        try:
            print("雪球 > ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
        except Exception as e:
            print(f"出错了：{e}")

        print()  # 空行分隔


async def main():
    """主入口"""
    config = load_config()
    agent_cfg = config.get("agent", {})
    memory_cfg = config.get("memory", {})

    # 创建自定义工具
    memory_path = memory_cfg.get("path", "SNOWBALL.md")
    tools = create_all_tools(memory_path=memory_path)

    # 创建 Agent
    agent = SnowballAgent(
        base_url=agent_cfg.get("base_url", "http://localhost:11434/v1"),
        model=agent_cfg.get("model", "qwen3:8b"),
        max_tool_iterations=agent_cfg.get("max_tool_iterations", 10),
        memory_path=memory_path,
        tools=tools,
    )

    try:
        await text_mode(agent)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
