"""鼠标坐标点击 — 用 Quartz.CoreGraphics 原生 API，无外部依赖"""
from __future__ import annotations

import time

from Quartz import (
    CGEventCreateMouseEvent,
    CGEventPost,
    kCGEventLeftMouseDown,
    kCGEventLeftMouseUp,
    kCGEventMouseMoved,
    kCGHIDEventTap,
    kCGMouseButtonLeft,
)


def click_at(x: float, y: float, settle: float = 0.1) -> None:
    """在屏幕逻辑坐标 (x, y) 处点一下左键。

    Args:
        x, y: 屏幕逻辑坐标（不是像素，与 AppleScript position 一致）
        settle: 移动/按下/松开之间的间隔秒数
    """
    mv = CGEventCreateMouseEvent(None, kCGEventMouseMoved, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, mv)
    time.sleep(settle)
    down = CGEventCreateMouseEvent(None, kCGEventLeftMouseDown, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.05)
    up = CGEventCreateMouseEvent(None, kCGEventLeftMouseUp, (x, y), kCGMouseButtonLeft)
    CGEventPost(kCGHIDEventTap, up)
