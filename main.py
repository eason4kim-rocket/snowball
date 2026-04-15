"""雪球（Snowball）— 你的本地 AI 助手

支持：终端文字模式 / 语音交互模式
"""

import argparse
import asyncio
import sys
from pathlib import Path

import yaml

from modules.agent import SnowballAgent
from modules.voice_in import RealtimeSTTListener
from modules.voice_out import MacOSSaySpeaker
from tools import create_all_tools


def load_config(config_path: str = "config.yaml") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def print_banner(mode: str = "text"):
    """打印启动横幅"""
    mode_label = "文字模式" if mode == "text" else "语音模式"
    print(f"""
  ╔══════════════════════════════════════╗
  ║    ❄️  雪球 Snowball v0.1.0          ║
  ║    你的本地 AI 助手 — {mode_label}       ║
  ║    输入 /quit 退出                    ║
  ╚══════════════════════════════════════╝
    """)


async def text_mode(agent: SnowballAgent, speaker: MacOSSaySpeaker | None = None):
    """终端文字交互模式"""
    print_banner("text")
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
            print("对话已清除")
            continue

        # 发送给 Agent
        try:
            print("雪球 > ", end="", flush=True)
            response = await agent.chat(user_input)
            print(response)
            if speaker:
                await speaker.speak(response)
        except Exception as e:
            print(f"出错了：{e}")

        print()


async def voice_mode(agent: SnowballAgent, speaker: MacOSSaySpeaker, config: dict):
    """语音交互模式：说话 → 雪球听懂 → 执行 → 语音回复"""
    print_banner("voice")

    voice_in_cfg = config.get("voice_in", {})
    listener = RealtimeSTTListener(
        language=voice_in_cfg.get("language", "zh"),
        model=voice_in_cfg.get("model", "medium"),
    )

    processing = False

    async def on_speech(text: str):
        nonlocal processing
        if processing:
            return
        processing = True

        print(f"\n老大 > {text}")
        try:
            print("雪球 > ", end="", flush=True)
            response = await agent.chat(text)
            print(response)
            await speaker.speak(response)
        except Exception as e:
            print(f"出错了：{e}")
        finally:
            processing = False
        print()

    await listener.start_listening(on_speech)

    print("雪球已就绪，直接说话就行 👊\n")

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n再见老大！")
    finally:
        await listener.stop_listening()


async def main():
    """主入口"""
    parser = argparse.ArgumentParser(description="雪球 — 你的本地 AI 助手")
    parser.add_argument("--voice", action="store_true", help="启用语音交互模式")
    parser.add_argument("--tts", action="store_true", help="启用语音输出（文字模式+语音回复）")
    args = parser.parse_args()

    config = load_config()
    agent_cfg = config.get("agent", {})
    memory_cfg = config.get("memory", {})
    voice_out_cfg = config.get("voice_out", {})

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

    # 创建 TTS（语音输出）
    speaker = None
    if args.voice or args.tts:
        speaker = MacOSSaySpeaker(
            voice=voice_out_cfg.get("voice", "Ting-Ting"),
            max_length=voice_out_cfg.get("max_length", 50),
        )

    try:
        if args.voice:
            await voice_mode(agent, speaker, config)
        else:
            await text_mode(agent, speaker)
    finally:
        await agent.close()


if __name__ == "__main__":
    asyncio.run(main())
