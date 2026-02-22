import asyncio
import time

class LLMRateLimiter:
    def __init__(self, min_interval=5.0):
        self.min_interval = min_interval
        self._lock = asyncio.Lock()
        self._last_call = 0.0

    async def wait(self):
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_call

            if elapsed < self.min_interval:
                sleep_time = self.min_interval - elapsed
                print(f"Enforcing {self.min_interval}s lag. Sleeping {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)

            self._last_call = time.time()
