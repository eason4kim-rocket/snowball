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
