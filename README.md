# ❄️ 雪球 Snowball

**完全本地的 Jarvis** — 说话 → 听懂 → 用 Ollama 大脑思考 → 操控 Mac → 语音回答你。

运行在 Mac Mini M4 上的私人 AI 助手，零云端依赖，隐私完全本地。

---

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                      你（老大）                          │
│          "雪球，打开音乐放周杰伦"                        │
└──────────────────────┬──────────────────────────────────┘
                       │ 麦克风
                       ▼
┌──────────────────────────────────────┐
│   模块 A：语音输入（可替换）         │
│   RealtimeSTT + Silero VAD           │
│   持续监听，检测到说话就转文字        │
└──────────────────────┬───────────────┘
                       │ 文字
                       ▼
┌──────────────────────────────────────────────────────────┐
│   模块 B：Agent 大脑（可替换）                           │
│   open-agent-sdk + Ollama qwen3.5:9b                     │
│                                                          │
│   工具：Accessibility / AppleScript / Mac控制 / 音乐 / 记忆│
│   SNOWBALL.md 持久记忆注入                                │
└──────────────────────┬───────────────────────────────────┘
                       │ 回复文字
                       ▼
┌──────────────────────────────────────┐
│   模块 C：语音输出（可替换）         │
│   macOS say / Edge-TTS / Kokoro TTS  │
└──────────────────────┬───────────────┘
                       │ 音频
                       ▼
                  电脑音响/耳机
```

三个模块通过标准接口通信，可独立替换。

---

## 快速开始

### 前置条件

- macOS（Mac Mini M4 推荐）
- Python 3.11+
- [Ollama](https://ollama.ai) (0.17.1+) 已安装并运行 `qwen3.5:9b` 模型

### 安装

```bash
# 克隆项目
git clone https://github.com/eason4kim-rocket/snowball.git
cd snowball

# 安装依赖
pip install -r requirements.txt

# 拉取 Ollama 模型
ollama pull qwen3.5:9b
```

### 运行

```bash
# 文字模式（终端交互）
python main.py

# 文字模式 + 语音回复
python main.py --tts

# 完整语音模式（说话 → 执行 → 语音回复）
python main.py --voice
```

---

## 配置

编辑 `config.yaml`：

```yaml
agent:
  base_url: http://localhost:11434/v1   # Ollama 地址
  model: qwen3.5:9b                     # LLM 模型（推荐，多模态+工具调用强）
  max_tool_iterations: 10

voice_in:
  enabled: false
  engine: realtime_stt
  language: zh
  model: medium
  wake_word:
    enabled: false
    words: ["雪球", "snowball"]

voice_out:
  enabled: false
  engine: edge_tts          # macos_say / edge_tts / kokoro
  voice: zh-CN-XiaoxiaoNeural
  max_length: 50

memory:
  path: SNOWBALL.md          # 持久记忆文件路径

fazm:
  enabled: false              # 已被 AccessibilityControl 替代
```

### TTS 引擎选择

| 引擎 | 特点 | 依赖 |
|------|------|------|
| `macos_say` | 最快，macOS 原生 | 无 |
| `edge_tts` | 自然度高，需联网 | `pip install edge-tts` |
| `kokoro` | 最自然，本地运行 | `pip install kokoro-onnx` + 模型文件 |

---

## 自定义工具

| 工具 | 用途 | 示例 |
|------|------|------|
| AccessibilityControl | 操控任意 App 的 GUI 元素（macOS Accessibility API） | "帮我在 Safari 点击提交按钮" |
| AppleScript | 打开 App、发邮件、控制 Safari | "打开音乐" |
| MusicControl | 控制 AlgerMusicPlayer | "播放周杰伦" |
| MacControl | 音量/亮度/窗口管理 | "声音大一点" |
| ReadMemory | 读取记忆文件 | 自动注入 |
| SearchMemory | 按章节/关键词搜索记忆 | 精准查找偏好 |
| WriteMemory | 写入/追加记忆 | 记住新偏好 |

> **注意：** FazmControl 已被 AccessibilityControl 替代，Fazm 默认关闭。AccessibilityControl 使用 macOS 原生 Accessibility API（通过 System Events），无需安装额外 App。

---

## 记忆系统

雪球通过 `SNOWBALL.md` 记住老大的偏好和习惯：

- 每轮对话自动刷新记忆到系统提示词
- 通过 `WriteMemory` 工具主动记住新信息
- 通过 `SearchMemory` 按章节或关键词精准查找
- 记忆 hash 缓存，无变化时跳过重建（性能优化）

---

## 测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 仅运行端到端测试
python -m pytest tests/test_e2e_linux.py -v
```

---

## 项目结构

```
snowball/
├── main.py                  # 启动入口
├── config.yaml              # 配置文件
├── SNOWBALL.md              # 雪球的持久记忆
├── ROADMAP.md               # 开发路线图
├── requirements.txt         # Python 依赖
│
├── modules/                 # 模块化，每层可独立替换
│   ├── voice_in/            # 模块 A：语音输入
│   ├── agent/               # 模块 B：Agent 大脑
│   └── voice_out/           # 模块 C：语音输出
│
├── tools/                   # 自定义工具
│   ├── accessibility_tool.py  # macOS Accessibility API（替代 Fazm）
│   ├── applescript_tool.py
│   ├── fazm_tool.py           # 已弃用，保留兼容
│   ├── mac_control_tool.py
│   ├── music_control_tool.py
│   ├── memory_tool.py
│   ├── retry.py               # 重试装饰器
│   └── safety.py              # 工具安全边界
│
└── tests/                   # 测试套件
```

---

## 开发路线

- [x] Phase 1 — Agent 核心（纯文字终端交互）
- [x] Phase 2 — 语音输入（RealtimeSTT）
- [x] Phase 3 — 语音输出（多引擎 TTS）
- [x] Phase 4 — 优化升级（Kokoro TTS、记忆增强、延迟优化、Accessibility API）

详见 [ROADMAP.md](ROADMAP.md)。

---

## License

Private project.
