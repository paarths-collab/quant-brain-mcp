import os
import json
import time

class CacheManager:

    def __init__(self, cache_dir="cache", ttl=3600):
        self.cache_dir = cache_dir
        self.ttl = ttl

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    def _get_path(self, key):
        # Sanitize key to be safe for filename
        safe_key = "".join([c for c in key if c.isalnum() or c in ('-', '_')]).strip()
        return os.path.join(self.cache_dir, f"{safe_key}.json")

    def get(self, key):
        path = self._get_path(key)

        if not os.path.exists(path):
            return None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            if time.time() - data["timestamp"] > self.ttl:
                return None

            return data["value"]
        except Exception as e:
            print(f"Cache read error: {e}")
            return None

    def set(self, key, value):
        path = self._get_path(key)

        try:
            with open(path, "w") as f:
                json.dump({
                    "timestamp": time.time(),
                    "value": value
                }, f, indent=4)
        except Exception as e:
            print(f"Cache write error: {e}")
