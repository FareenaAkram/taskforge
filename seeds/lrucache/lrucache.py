"""lrucache: an LRU cache with optional TTL, and a token-bucket rate limiter."""

from collections import OrderedDict


class LRUCache:
    """Least-recently-used cache with optional per-entry time-to-live (seconds)."""

    def __init__(self, capacity, ttl=None, clock=None):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock if clock is not None else (lambda: 0)
        self._data = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _expired(self, stamp):
        return self.ttl is not None and self.clock() - stamp >= self.ttl

    def get(self, key, default=None):
        if key in self._data:
            value, stamp = self._data[key]
            if self._expired(stamp):
                del self._data[key]
            else:
                self._data.move_to_end(key)
                self.hits += 1
                return value
        self.misses += 1
        return default

    def put(self, key, value):
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, self.clock())
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def purge(self):
        """Drop expired entries and return how many were removed."""
        stale = [k for k, (_, stamp) in self._data.items() if self._expired(stamp)]
        for k in stale:
            del self._data[k]
        return len(stale)

    def __len__(self):
        self.purge()
        return len(self._data)

    def hit_rate(self):
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


class TokenBucket:
    """Rate limiter: `rate` tokens per second, holding at most `burst` tokens."""

    def __init__(self, rate, burst, clock):
        self.rate = rate
        self.burst = burst
        self.clock = clock
        self.tokens = burst
        self.updated = clock()

    def _refill(self):
        now = self.clock()
        elapsed = now - self.updated
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.updated = now

    def allow(self, cost=1):
        """Consume `cost` tokens if available."""
        self._refill()
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False

    def wait_time(self, cost=1):
        """Seconds until `cost` tokens will be available (0 if available now)."""
        self._refill()
        if self.tokens >= cost:
            return 0.0
        return (cost - self.tokens) / self.rate
