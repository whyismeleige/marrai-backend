from dataclasses import dataclass, field
import time


@dataclass
class FakeRedis:
    """In-memory stand-in for the redis.asyncio methods we actually use."""

    store: dict[str, list] = field(default_factory=dict)  # key -> [value, expires_at]

    def _live(self, key: str) -> bool:
        entry = self.store.get(key)
        if entry is None:
            return False
        if entry[1] is not None and entry[1] <= time.monotonic():
            del self.store[key]
            return False
        return True

    async def incr(self, key: str) -> int:
        if self._live(key):
            self.store[key][0] += 1
        else:
            self.store[key] = [1, None]
        return int(self.store[key][0])

    async def expire(self, key: str, seconds: int) -> bool:
        if self._live(key):
            self.store[key][1] = time.monotonic() + seconds
            return True
        return False

    async def ttl(self, key: str) -> int:
        if not self._live(key):
            return -2
        return max(1, int(self.store[key][1] - time.monotonic()))

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        self.store.clear()