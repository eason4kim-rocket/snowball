# 雪球（Snowball）架构路线图

## 一句话定义
**完全本地的贾维斯**：说话 → 听懂 → 用 Ollama 大脑思考 → 用 Fazm 操纵 Mac → 用语音回答你。

---

## 整体架构（全栈 Python，模块化，后期可替换）

```
┌─────────────────────────────────────────────────────────┐
│                      你（老大）                          │
│          "雪球，打开音乐放周杰伦"                        │
└──────────────────────┬──────────────────────────────────┘
                       │ 麦克风
                       ▼
┌──────────────────────────────────────┐
│   模块 A：语音输入层（可替换）       │
│   RealtimeSTT                        │
│   Silero VAD + faster-whisper        │
│   持续监听，检测到说话就转文字        │
└──────────────────────┬───────────────┘
                       │ 文字（标准接口）
                       ▼
┌──────────────────────────────────────────────────────────┐
│   模块 B：Agent 大脑（可替换）                           │
│   open-agent-sdk-python                                  │
│                                                          │
│   - Ollama qwen3.5:9b（本地 LLM）                       │
│   - 35 内置工具（Bash/Read/Write/Glob/Grep/Web/Agent）  │
│   - 自定义工具（AppleScript/Fazm/Mac 控制）             │
│   - 子 Agent / MCP / Hook / 会话持久化                  │
│   - SNOWBALL.md 记忆注入                                 │
│                                                          │
│   LLM 决策 ──► 调工具 ──► 看结果 ──► 继续/结束         │
└──────────────────────┬───────────────────────────────────┘
                       │ 回复文字（标准接口）
                       ▼
┌──────────────────────────────────────┐
│   模块 C：语音输出层（可替换）       │
│   RealtimeTTS                        │
│   macOS say（v1）→ Kokoro TTS（v2）  │
│   "好的老大，正在为您播放周杰伦"      │
└──────────────────────┬───────────────┘
                       │ 音频
                       ▼
                  电脑音响/耳机
```

**模块化设计**：A/B/C 三个模块通过标准接口通信，后期可独立替换：
- 模块 B 可替换为 open-agent-sdk-typescript（加 HTTP bridge）
- 模块 A/C 可替换为其他 STT/TTS 引擎
- 工具层可热插拔（define_tool / MCP Server）

---

## 技术栈

| 组件 | 技术 | 说明 | 可替换为 |
|------|------|------|----------|
| **Agent 核心** | open-agent-sdk-python | Claude Code 架构，35 工具，Ollama 原生支持 | open-agent-sdk-typescript |
| **LLM** | Ollama + qwen3.5:9b | 本地，M4 24GB 流畅，多模态+工具调用强 | 任意 OpenAI-compatible |
| **语音识别** | RealtimeSTT（faster-whisper + Silero VAD） | 一行代码 always-listening | whisper.cpp / MLX Whisper |
| **语音合成** | RealtimeTTS（macOS say → Kokoro） | 先快速跑通，再换自然声音 | Kokoro / Piper / Edge TTS |
| **电脑控制（简单）** | AppleScript + osascript | Music/Mail/Finder/Safari，秒级 | — |
| **电脑控制（复杂）** | Fazm App（分布式通知） | Claude Computer Use，精准但需联网 | pyobjc / pyautogui |
| **持久记忆** | SNOWBALL.md | 偏好、联系人、习惯 | SQLite / 向量数据库 |

---

## Fazm 集成方式

Fazm 是 macOS 桌面 App（Swift/SwiftUI），从 Python 控制它：

### 方式 1：分布式通知（零依赖）
```bash
# 发命令给 Fazm
xcrun swift -e 'import Foundation; DistributedNotificationCenter.default().postNotificationName(
  .init("com.fazm.control"), object: nil,
  userInfo: ["command": "sendFollowUp:打开音乐"],
  deliverImmediately: true
); RunLoop.current.run(until: Date(timeIntervalSinceNow: 1.0))'

# 读取状态
xcrun swift -e '... ["command": "getState"] ...'
cat /tmp/fazm-control-state.json
```

### 方式 2：直接注入查询
```bash
xcrun swift -e 'import Foundation; DistributedNotificationCenter.default().postNotificationName(
  .init("com.fazm.testQuery"), object: nil,
  userInfo: ["text": "打开音乐播放周杰伦"],
  deliverImmediately: true
); RunLoop.current.run(until: Date(timeIntervalSinceNow: 1.0))'
```

### 集成策略
```
简单指令（打开App/播放音乐/发邮件）
  → AppleScript（最快，< 1 秒，全本地）

复杂 GUI 操作（点击按钮/填表单/跨App操作）
  → Fazm 分布式通知（需联网，但精准）
```

---

## 开发路线（4 个阶段）

### Phase 1 — Agent 核心（纯文字，终端交互）
> 目标：雪球能在终端里接收文字命令，调用工具真正操控电脑

- [ ] 安装 open-agent-sdk-python（`pip install open-agent-sdk`）
- [ ] 配置 Ollama 接入（`base_url=http://localhost:11434/v1`）
- [ ] 写雪球 System Prompt + SNOWBALL.md 记忆
- [ ] 实现自定义工具：AppleScript（Music/Mail/Finder）、Fazm 控制
- [ ] 终端交互测试："打开音乐"→ 雪球用工具执行
- **验收**：终端输入"打开 Music 放周杰伦"，它真的打开并播放

### Phase 2 — 加语音输入
> 目标：说话，雪球听到并处理

- [ ] pip install RealtimeSTT
- [ ] 模块 A 封装：always-listening（无需唤醒词）
- [ ] 语音 → 文字 → 传入 Agent
- **验收**：对着麦克风说命令，雪球正确执行

### Phase 3 — 加语音输出
> 目标：雪球用声音回复你

- [ ] pip install RealtimeTTS
- [ ] 模块 C 封装：macOS `say`（中文 Ting-Ting）
- [ ] 语音回复自动截短（1-2 句话）
- [ ] 主循环打通：说话 → 执行 → 语音回复
- **验收**：完整对话"雪球打开音乐"→ "好的老大，为您播放"

### Phase 4 — 优化升级
> 目标：更自然、更快、更聪明

- [ ] 升级 TTS → Kokoro TTS（更自然的声音）
- [ ] SNOWBALL.md 记忆自动更新（记住偏好）
- [ ] 子 Agent（复杂多步任务并行）
- [ ] 延迟优化（简单指令 < 1.5 秒）
- [ ] 更多工具：日历、提醒事项、截图分析
- [ ] 考虑替换为 open-agent-sdk-typescript（如需更高性能）

---

## 项目文件结构

```
snowball/
├── ROADMAP.md                  ← 这个文件
├── SNOWBALL.md                 ← 雪球的持久记忆
├── setup.sh                    ← 一键安装脚本
├── requirements.txt            ← Python 依赖
├── config.yaml                 ← 配置（模型/声音/语言等）
├── main.py                     ← 启动入口
│
├── modules/                    ← 模块化，每层可独立替换
│   ├── voice_in/               ← 模块 A：语音输入
│   │   ├── __init__.py
│   │   ├── listener.py         ← RealtimeSTT 封装
│   │   └── base.py             ← 标准接口（ABC）
│   │
│   ├── agent/                  ← 模块 B：Agent 大脑
│   │   ├── __init__.py
│   │   ├── snowball_agent.py   ← open-agent-sdk 封装
│   │   ├── system_prompt.py    ← 雪球人格 + 工具定义
│   │   └── base.py             ← 标准接口（ABC）
│   │
│   └── voice_out/              ← 模块 C：语音输出
│       ├── __init__.py
│       ├── speaker.py          ← RealtimeTTS 封装
│       └── base.py             ← 标准接口（ABC）
│
└── tools/                      ← 自定义工具（open-agent-sdk define_tool）
    ├── __init__.py
    ├── applescript_tool.py      ← AppleScript（Music/Mail/Finder/Safari）
    ├── fazm_tool.py             ← Fazm 分布式通知控制
    ├── mac_control_tool.py      ← macOS 窗口/App 控制
    ├── screenshot_tool.py       ← screencapture 截图
    └── memory_tool.py           ← 读写 SNOWBALL.md
```

---

## 延迟目标（M4 24GB）

| 步骤 | 目标延迟 |
|------|----------|
| VAD 检测到说话结束 | ~0.5 秒 |
| STT 转文字 | ~1-2 秒 |
| LLM 首次 Token | ~0.5 秒 |
| 工具执行（AppleScript） | ~0.3 秒 |
| 工具执行（Fazm 复杂操作） | ~3-5 秒 |
| TTS 出声 | < 0.5 秒 |
| **简单指令总延迟** | **< 3 秒** |
| **复杂多步任务** | **< 8 秒** |

---

## 参考项目

| 项目 | 用途 | 位置 |
|------|------|------|
| open-agent-sdk-python | Agent 核心 | `github.com/codeany-ai/open-agent-sdk-python` |
| open-agent-sdk-typescript | Agent 核心（备选） | `github.com/codeany-ai/open-agent-sdk-typescript` |
| Fazm | Mac 电脑控制（手脚） | `/Users/eason/Documents/skills/agent/fazm-main/` |
| ultraworkers/claw-code | 架构参考 | `github.com/ultraworkers/claw-code` |
| tanbiralam/claude-code | 架构参考 | `github.com/tanbiralam/claude-code` |

---

## 下一步

按 Phase 1 → 2 → 3 → 4 顺序实现。
Phase 1 只需终端 + 文字就能验证核心 Agent 能力，随时可以测试。
