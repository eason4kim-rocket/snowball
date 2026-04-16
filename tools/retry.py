"""工具重试与 fallback 机制"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Callable

logger = logging.getLogger("snowball.tools.retry")


def with_retry(
    max_retries: int = 2,
    retry_delay: float = 0.5,
    fallback: Callable | None = None,
):
    """工具重试装饰器。

    用法::

        @with_retry(max_retries=2, fallback=my_fallback_fn)
        async def my_tool(args: dict) -> dict:
            ...

    参数:
        max_retries: 最大重试次数（不含首次执行）
        retry_delay: 重试间隔（秒）
        fallback: 所有重试失败后的备用函数，签名与原函数相同
    """

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(args: dict) -> dict:
            last_error = None
            for attempt in range(1 + max_retries):
                try:
                    result = await fn(args)
                    # 工具返回 {"error": ...} 也算失败
                    if isinstance(result, dict) and "error" in result:
                        last_error = result["error"]
                        if attempt < max_retries:
                            logger.warning(
                                "工具 %s 第 %d 次执行返回错误: %s，%0.1fs 后重试",
                                fn.__name__, attempt + 1, last_error, retry_delay,
                            )
                            await asyncio.sleep(retry_delay)
                            continue
                    else:
                        return result
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        logger.warning(
                            "工具 %s 第 %d 次执行异常: %s，%0.1fs 后重试",
                            fn.__name__, attempt + 1, last_error, retry_delay,
                        )
                        await asyncio.sleep(retry_delay)
                    continue

            # 所有重试失败，尝试 fallback
            if fallback is not None:
                logger.info("工具 %s 重试耗尽，执行 fallback", fn.__name__)
                try:
                    return await fallback(args)
                except Exception as e:
                    return {"error": f"fallback 也失败：{e}（原始错误：{last_error}）"}

            return {"error": f"重试 {max_retries} 次后仍失败：{last_error}"}

        return wrapper

    return decorator
