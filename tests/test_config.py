"""配置加载测试 — 直接测试 load_config 函数（不导入 main 避免 RealtimeSTT 依赖）"""

from pathlib import Path

import yaml


def load_config(config_path: str = "config.yaml") -> dict:
    """复制自 main.py 的 load_config，避免导入 main 触发全部依赖"""
    path = Path(config_path)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def test_load_config_default():
    """测试默认配置加载"""
    config = load_config("config.yaml")
    assert isinstance(config, dict)
    assert "agent" in config
    assert "voice_out" in config
    assert "memory" in config


def test_load_config_missing():
    """测试缺失配置文件返回空字典"""
    config = load_config("nonexistent.yaml")
    assert config == {}


def test_config_values():
    """测试配置值正确性"""
    config = load_config("config.yaml")
    assert config["agent"]["model"] == "qwen3.5:9b"
    assert config["memory"]["path"] == "SNOWBALL.md"
    assert config["voice_out"]["engine"] in ("macos_say", "edge_tts", "kokoro")
