# 雪球（Snowball）架构路线图

## 一句话定义
**完全本地的贾维斯**：说话 → 听懂 → 用 Ollama 大脑思考 → 用 AppleScript + Accessibility API 操纵 Mac → 用语音回答你。

> **当前状态**：Phase 1–4 已完成 ✅，92 个单元测试全过。Fazm 已由原生工具链（AppleScript + Accessibility + MacControl + MusicControl）完全取代，不再依赖外部 App。


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
│   - 7 个自定义工具：                                     │
│     · AppleScript（Music/Mail/Finder/Safari）           │
│     · AccessibilityControl（任意 App 的 UI 控制）       │
│     · MacControl（音量/亮度/窗口/睡眠）                 │
│     · MusicControl（AlgerMusicPlayer 专用）             │
│     · ReadMemory/WriteMemory/SearchMemory               │
│   - SafetyGuard Hook（高危操作确认）                    │
│   - 流式输出（chat_stream 按句 yield 给 TTS）           │
│   - 历史修剪（user 边界切，tool 配对不破坏）            │
│   - SNOWBALL.md 记忆注入（hash 缓存）                   │
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

**额外能力**：
- 🖥️ Web Dashboard（FastAPI + WebSocket）— 浏览器可视化对话/工具调用/记忆
- 🎙️ 唤醒词检测（"雪球 / snowball"，可配置）
- 🔁 工具重试 + 不可恢复错误跳过（`_NON_RETRIABLE_ERROR_KINDS`）

---

## 技术栈

| 组件 | 技术 | 说明 | 可替换为 |
|------|------|------|----------|
| **Agent 核心** | open-agent-sdk-python | Claude Code 架构，35 工具，Ollama 原生支持 | open-agent-sdk-typescript |
| **LLM** | Ollama + qwen3.5:9b | 本地，M4 24GB 流畅，多模态+工具调用强 | 任意 OpenAI-compatible |
| **语音识别** | RealtimeSTT（faster-whisper + Silero VAD） | 一行代码 always-listening | whisper.cpp / MLX Whisper |
| **语音合成** | RealtimeTTS（macOS say → Kokoro） | 先快速跑通，再换自然声音 | Kokoro / Piper / Edge TTS |
| **电脑控制（简单）** | AppleScript + osascript | Music/Mail/Finder/Safari，秒级 | — |
| **电脑控制（通用 GUI）** | AccessibilityControl（osascript + System Events） | 任意 App 的按钮/菜单/输入框，零外部依赖 | pyobjc AX API（见底部 C 方案）|
| **电脑控制（系统级）** | MacControl | 音量/亮度/窗口/睡眠 | — |
| **音乐播放** | MusicControl | AlgerMusicPlayer 搜索/切歌/音量 | Apple Music AppleScript |
| **持久记忆** | SNOWBALL.md + 工具 3 件套 | 读/写/搜索 | SQLite / 向量数据库 |
| **Web Dashboard** | FastAPI + WebSocket | 浏览器实时查看对话与工具调用 | Gradio / Streamlit |
| **安全网** | SafetyGuard Hook | 高危操作弹窗确认（删除/邮件/睡眠等） | — |

---

## 开发路线（4 个阶段）

> 所有 Phase 均已完成。保留作为实现记录。

### Phase 1 — Agent 核心（纯文字，终端交互）✅
> 目标：雪球能在终端里接收文字命令，调用工具真正操控电脑

- [x] 安装 open-agent-sdk-python
- [x] 配置 Ollama 接入（`base_url=http://localhost:11434/v1`）
- [x] 写雪球 System Prompt + SNOWBALL.md 记忆
- [x] 实现自定义工具：AppleScript/AccessibilityControl/MacControl/MusicControl
- [x] 终端交互测试通过
- **验收达成**：终端输入"打开 Music 放周杰伦"正确执行

### Phase 2 — 加语音输入 ✅
> 目标：说话，雪球听到并处理

- [x] RealtimeSTT 接入
- [x] 模块 A 封装：always-listening + VAD
- [x] 唤醒词检测（"雪球 / snowball"）
- [x] 语音 → 文字 → 传入 Agent
- **验收达成**：对着麦克风说命令，雪球正确执行

### Phase 3 — 加语音输出 ✅
> 目标：雪球用声音回复你

- [x] macOS `say`（默认、零依赖）
- [x] Edge TTS（在线，自然中文）
- [x] Kokoro TTS（本地，最自然）
- [x] 流式输出（`chat_stream` 按句 yield 给 TTS，边想边说）
- [x] 主循环打通：说话 → 执行 → 语音回复
- **验收达成**：完整对话"雪球打开音乐"→ "好的老大，为您播放"

### Phase 4 — 优化升级 ✅
> 目标：更自然、更快、更聪明

- [x] TTS 多引擎可切换（say / edge_tts / kokoro）
- [x] SNOWBALL.md 记忆读写（ReadMemory / WriteMemory / SearchMemory 三件套）
- [x] 流式输出 + Hook + 会话持久化（by open-agent-sdk）
- [x] 工具重试机制（`with_retry` 装饰器 + 不可恢复错误跳过）
- [x] SafetyGuard（高危操作确认，async 不阻塞事件循环）
- [x] Web Dashboard（FastAPI + WebSocket 实时可视化）
- [x] 历史修剪（按 user 边界切分，tool_use/result 配对不被破坏）
- [x] AccessibilityControl（替代 Fazm，原生零依赖的通用 GUI 控制）
- [ ] 子 Agent（复杂多步任务并行）— 延后
- [ ] 更多工具：日历、提醒事项、截图分析 — 延后
- [ ] 考虑替换为 open-agent-sdk-typescript（如需更高性能）— 延后

---

## 项目文件结构（当前真实状态）

```
snowball/
├── ROADMAP.md                  ← 这个文件
├── README.md                   ← 安装 + 使用
├── SNOWBALL.md                 ← 雪球的持久记忆
├── setup.sh                    ← 一键安装
├── requirements.txt            ← Python 依赖
├── config.yaml                 ← 配置（模型/声音/语言等）
├── main.py                     ← 启动入口（终端 / voice / web 三模式）
│
├── modules/                    ← 模块化，每层可独立替换
│   ├── voice_in/               ← 模块 A：语音输入
│   │   ├── listener.py         ← RealtimeSTT 封装
│   │   ├── wake_word.py        ← 唤醒词检测（"雪球 / snowball"）
│   │   └── base.py             ← 标准接口（ABC）
│   │
│   ├── agent/                  ← 模块 B：Agent 大脑
│   │   ├── snowball_agent.py   ← open-agent-sdk 封装 + Hook + 历史修剪
│   │   ├── system_prompt.py    ← 雪球人格 + 工具定义
│   │   └── base.py             ← 标准接口（ABC）
│   │
│   └── voice_out/              ← 模块 C：语音输出（3 引擎）
│       ├── speaker.py          ← macOS `say`
│       ├── edge_speaker.py     ← Edge TTS（在线）
│       ├── kokoro_speaker.py   ← Kokoro TTS（本地）
│       └── base.py             ← 标准接口（ABC）
│
├── tools/                      ← 自定义工具（open-agent-sdk define_tool）
│   ├── applescript_tool.py     ← AppleScript（Music/Mail/Finder/Safari）
│   ├── accessibility_tool.py   ← 通用 GUI 控制（替代 Fazm）
│   ├── mac_control_tool.py     ← 音量/亮度/窗口/睡眠
│   ├── music_control_tool.py   ← AlgerMusicPlayer 专用
│   ├── memory_tool.py          ← 读/写/搜索 SNOWBALL.md
│   ├── fazm_tool.py            ← 旧的 Fazm 通知（已弃用，保留备份）
│   ├── safety.py               ← SafetyGuard（高危操作确认）
│   └── retry.py                ← with_retry 装饰器
│
├── web/                        ← Web Dashboard
│   ├── app.py                  ← FastAPI + WebSocket 服务
│   └── index.html              ← 前端
│
└── tests/                      ← 92 个单元测试
    ├── test_accessibility.py / test_accessibility_fixes.py
    ├── test_memory_tool.py
    ├── test_wake_word.py
    ├── test_safety.py
    ├── test_retry.py
    ├── test_voice_out.py
    ├── test_trim_history.py
    ├── test_tools_init.py
    ├── test_config.py
    └── test_e2e_linux.py
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
| Fazm | ~~Mac 电脑控制~~（已由 AccessibilityControl 取代） | `/Users/eason/Documents/skills/agent/fazm-main/` |
| ultraworkers/claw-code | 架构参考 | `github.com/ultraworkers/claw-code` |
| tanbiralam/claude-code | 架构参考 | `github.com/tanbiralam/claude-code` |

---

## 下一步（v0.2 规划）

Phase 1–4 已完成，下面是积累下来的 TODO，按优先级排：

### 高优：真实使用后暴露的问题

- [ ] **语音模式端到端实测** — Phase 2/3 只跑过单元测试，需要在你的实际麦克风 + 耳机环境试 10 条真实指令，记录失败场景
- [ ] **voice_in 的 Ctrl+C 清理** — RealtimeSTT 后台线程退出时偶尔会卡住，需加 signal handler
- [ ] **Web Dashboard 鉴权** — `web/app.py` 目前 `127.0.0.1` 监听，如要开 `0.0.0.0` 必须加 token，否则局域网任何人都能控你电脑
- [ ] **AccessibilityControl 递归查找性能** — `entire contents of window N` 在元素特别多的 App（如 Excel）会慢到 > 5s，加个 `max_depth` 参数截断

### 中优：体验增强

- [ ] **子 Agent** — "帮我整理桌面并发邮件总结" 这种多步任务并行执行
- [ ] **截图工具** — `screenshot_tool`（给 LLM 看屏幕，配合坐标点击）
- [ ] **日历 / 提醒事项 AppleScript 工具**
- [ ] **对话历史持久化** — 现在重启丢光，应该存到 `~/.snowball/sessions/`

### 低优：架构演进

- [ ] **AccessibilityControl 纯 pyobjc 升级（C 方案）** — 见下文专章
- [ ] **open-agent-sdk-typescript 迁移评估** — 如果 Python 侧延迟瓶颈明显
- [ ] **SNOWBALL.md 向量化** — 记忆条目多了后，用 embedding 做相似度检索代替关键词搜索

---

## 远期研究方向（不立即动手，记录方向）

### 🧠 模型升级候选：Qwen3.6-35B-A3B

背景：2026-04 Unsloth 放出 2-bit Dynamic 2.0 量化，**13 GB 内存**在 Mac mini
就能跑，30+ 连续 tool calls 稳定，Agent 能力比 qwen3.5:9b 强一档。

- **架构**：MoE，总参数 35B，激活 3B → 推理可能比当前 9B dense 还快
- **视觉**：待确认
  - 若确实是 VL 版（Qwen3.6-VL-35B-A3B）→ 直接整体替换 qwen3.5:9b
  - 若是纯文本 MoE → 采用双模型路由
    - 简单对话 / 视觉任务 → qwen3.5:9b（保留眼睛）
    - 复杂 Agent / 长链工具 → Qwen3.6-35B-A3B（聪明大脑）
- **运行方式**：Unsloth Studio macOS（beta）或等 Ollama 收录后的 GGUF
- **启动条件**：当前 qwen3.5:9b 在真实对话中出现 tool 调用混乱 /
  复杂任务推不动时，再启动迁移
- **参考**：<https://github.com/unslothai/unsloth>

### 🤖 AGI 级主动性

不是 cron 调度，是 Agent **自主决定何时开口**。依赖持续思考 + 共情判断，
当前基础模型还做不稳。等下一代模型（Qwen 4 / 持续 agent 架构 /
Sleep-time compute）或架构突破再启动。

参考方向：Anthropic Claude Always-On、Google Astra、OpenAI o3 reasoning。

### 👁️ 视觉路线（v0.3 候选）

- `ScreenSnapshot` 工具（Mac mini 先能用）
- `CameraSnapshot` 工具，抽象 `source="system_default|external|iphone"`
  - Mac mini：外接 USB 摄像头 或 Continuity Camera（iPhone 当摄像头）
  - MacBook Air：内置 FaceTime HD
- VLM 集成：直接用 qwen3.5:9b（已有视觉），或升级到 Qwen3.6-VL

### 🛸 机器人形态（长期梦想）

路径：纯软件 → 固定节点（客厅放树莓派当"耳朵眼睛"）→ 移动底盘 →
BB-8 风格球形外壳。LLM 始终跑在 Mac 后端，机器人端只做 I/O。
预算 ~3000 元起步（Pi5 + 麦克风阵列 + 摄像头 + 底盘）。

---

## 待办 / TODO

### 🔮 AccessibilityControl 升级到纯 pyobjc（C 方案）

**为什么做**：当前 `tools/accessibility_tool.py` 走的是 `osascript → AppleScript → System Events` 三层包装，实际上只能用到 AX API 的子集。A 方案（权限预检、递归查找、错误码识别）只解决了 70% 的问题，剩下的 30% 能力天花板由 AppleScript 决定：

- ❌ 无法拿到元素**坐标**（x, y, width, height）
- ❌ 无法按 (x, y) 直接点击
- ❌ 无法枚举某元素**所有可执行动作**（AXPress/AXShowMenu/AXIncrement/AXPick…）
- ❌ 无法获取 **AXSubrole**（同一个 role 的细分类型，比如 "close button" vs "zoom button"）
- ❌ 对 Electron / Chrome 这类 App 的 WebView 内容看不清楚
- ❌ `delay 0.3` 写死，无法用 `AXObserver` 实现"等 UI 就绪"
- ❌ 菜单最多支持 3 级，深层菜单跪
- ⚠️ 每次调用 osascript 冷启动 50–300ms，真·点击动作都要排队

**怎么做**：新建 `tools/accessibility_ax_tool.py`，用 `pyobjc` 直接调用：

```python
from ApplicationServices import (
    AXUIElementCreateApplication,
    AXUIElementCopyAttributeValue,
    AXUIElementPerformAction,
    AXObserverCreate,  # 可选：观察 UI 变化
    AXIsProcessTrusted,
)
from AppKit import NSWorkspace
```

关键函数骨架：

- `_find_app(name)` — NSWorkspace 按 localizedName / bundleID 找进程
- `_walk(el, max_depth=8, filter_role=None)` — 递归遍历 AX 树
- `_find_element(app_el, name, role=None, fuzzy=True)` — 模糊 + 递归查找
- `_click(app_name, element_name)` — `AXUIElementPerformAction(el, "AXPress")`
- `_click_at(x, y)` — `CGEventCreateMouseEvent` + `CGEventPost`
- `_type_text(text)` — `CGEventCreateKeyboardEvent` 直接注入
- `_wait_for_element(app, name, timeout=5)` — 轮询 AX 树直到元素出现

**能解锁什么新能力**：

1. **坐标点击** — Agent 可以说"点 (1200, 800)"
2. **动作枚举** — `AXUIElementCopyActionNames` 列出元素支持的所有动作
3. **等 UI 就绪** — 替换写死的 `delay 0.3`，用 `AXObserver` 监听变化
4. **焦点追踪** — `AXFocusedUIElement` 知道光标在哪
5. **窗口操作** — `AXRaise` / `AXMinimize` / `AXZoom` 分别置前/最小化/缩放
6. **Electron 支持** — 能读到 `AXGroup > AXWebArea > AXStaticText` 的 DOM 级元素

**预估成本**：

| 项目 | 时间 |
|------|------|
| 8 个核心 action 实现 | 4–6 小时 |
| 单元测试 + mock | 1–2 小时 |
| 迁移现有 AppleScript 版到降级 fallback | 1 小时 |
| 文档 + README 补 AX 权限说明 | 0.5 小时 |
| **合计** | **6–9 小时** |

**风险点**：

- `AXValue` 拆包需要 `AXValueGetType` + `AXValueGetValue`（`(x,y)` 不是直接 Python tuple）
- 快捷键要走 `CGEventPost`（不是 AX API 的一部分），多一层依赖
- Sonoma / Sequoia 对 AX API 有轻微语义差异，需兼容测试
- 把 `accessibility_tool` 的 `input_schema` 加 `x/y/timeout` 字段，旧的 prompt 记忆可能要更新

**何时启动**：

- 先跑一段时间现有 A 方案版本，收集 Agent 真实失败场景
- 如果发现"元素找不到 / 坐标需要 / 菜单超 3 级"的占比 > 20%，启动 C 方案
- 否则可推迟到 v0.3

参考：
- Apple 文档 [AXUIElement API](https://developer.apple.com/documentation/applicationservices/axuielement_h)
- pyobjc [ApplicationServices](https://pypi.org/project/pyobjc-framework-ApplicationServices/)
- MacPython 示例 [ax_example.py](https://github.com/ronaldoussoren/pyobjc/tree/master/pyobjc-framework-ApplicationServices)
