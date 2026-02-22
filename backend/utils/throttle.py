import asyncio
import random

class Throttle:

    def __init__(self, min_delay=0.3, max_delay=1.2):
        self.min_delay = min_delay
        self.max_delay = max_delay

    async def wait(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        await asyncio.sleep(delay)
