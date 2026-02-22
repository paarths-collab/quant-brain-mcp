import asyncio
import time

class LLMCooldownManager:
    def __init__(self):
        self._cooldown_until = 0
        self._lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Checks if a global cooldown is active and waits if so."""
        # Check without lock first for performance
        if time.time() >= self._cooldown_until:
             return

        async with self._lock:
            now = time.time()
            if now < self._cooldown_until:
                remaining = self._cooldown_until - now
                if remaining > 0.1:
                    print(f"TPM hit. Global cooldown active. Sleeping {remaining:.2f}s...")
                    await asyncio.sleep(remaining)

    async def trigger_cooldown(self, seconds=60):
        """Activates the global cooldown."""
        async with self._lock:
            # Only extend if not already further out
            now = time.time()
            new_target = now + seconds
            if new_target > self._cooldown_until:
                self._cooldown_until = new_target
                print(f"Activating {seconds}s global LLM cooldown.")
