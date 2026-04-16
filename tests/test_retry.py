"""工具重试机制测试"""

import asyncio

from tools.retry import with_retry


class TestRetry:
    def test_success_no_retry(self):
        call_count = 0

        @with_retry(max_retries=2)
        async def good_tool(args):
            nonlocal call_count
            call_count += 1
            return {"result": "ok"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(good_tool({}))
            assert result == {"result": "ok"}
            assert call_count == 1
        finally:
            loop.close()

    def test_error_then_success(self):
        call_count = 0

        @with_retry(max_retries=2, retry_delay=0.01)
        async def flaky_tool(args):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {"error": "临时错误"}
            return {"result": "ok"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(flaky_tool({}))
            assert result == {"result": "ok"}
            assert call_count == 2
        finally:
            loop.close()

    def test_all_retries_fail(self):
        call_count = 0

        @with_retry(max_retries=2, retry_delay=0.01)
        async def bad_tool(args):
            nonlocal call_count
            call_count += 1
            return {"error": "持续错误"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(bad_tool({}))
            assert "error" in result
            assert "重试" in result["error"]
            assert call_count == 3  # 1 initial + 2 retries
        finally:
            loop.close()

    def test_exception_retry(self):
        call_count = 0

        @with_retry(max_retries=1, retry_delay=0.01)
        async def exc_tool(args):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("boom")
            return {"result": "recovered"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(exc_tool({}))
            assert result == {"result": "recovered"}
            assert call_count == 2
        finally:
            loop.close()

    def test_fallback(self):
        async def my_fallback(args):
            return {"result": "fallback_value"}

        @with_retry(max_retries=1, retry_delay=0.01, fallback=my_fallback)
        async def bad_tool(args):
            return {"error": "always fails"}

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(bad_tool({}))
            assert result == {"result": "fallback_value"}
        finally:
            loop.close()
