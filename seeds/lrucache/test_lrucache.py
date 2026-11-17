import pytest

from lrucache import LRUCache, TokenBucket


class Clock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_capacity_must_be_positive():
    """Capacity must be a positive number"""
    with pytest.raises(ValueError):
        LRUCache(0)
    with pytest.raises(ValueError):
        LRUCache(-1)
    assert LRUCache(1).capacity == 1


def test_put_and_get():
    """Stored values can be read back, with a default for missing keys"""
    c = LRUCache(2)
    c.put("a", 1)
    assert c.get("a") == 1
    assert c.get("missing") is None
    assert c.get("missing", "dflt") == "dflt"


def test_evicts_least_recently_used():
    """The oldest untouched entry is evicted first when capacity is exceeded"""
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert c.get("a") is None
    assert c.get("b") == 2
    assert c.get("c") == 3


def test_get_refreshes_recency():
    """Reading an entry protects it from eviction"""
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    c.put("c", 3)
    assert c.get("b") is None
    assert c.get("a") == 1


def test_put_existing_key_updates_value_and_recency():
    """Re-putting a key updates its value and makes it most recent"""
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 3)
    c.put("c", 4)
    assert c.get("b") is None
    assert c.get("a") == 3


def test_updating_a_key_does_not_grow_the_cache():
    """Overwriting an existing key never counts twice towards capacity"""
    c = LRUCache(2)
    c.put("a", 1)
    c.put("a", 2)
    c.put("b", 3)
    assert len(c) == 2
    assert c.get("a") == 2
    assert c.get("b") == 3


def test_len_is_bounded_by_capacity():
    """The cache never holds more than `capacity` entries"""
    c = LRUCache(3)
    for i in range(5):
        c.put(i, i)
    assert len(c) == 3
    assert c.get(0) is None
    assert c.get(2) == 2


def test_capacity_one():
    """A capacity-one cache keeps only the latest entry"""
    c = LRUCache(1)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") is None
    assert c.get("b") == 2


def test_falsy_values_are_cached():
    """Falsy values such as 0 and empty strings are real hits"""
    c = LRUCache(2)
    c.put("zero", 0)
    assert c.get("zero", "dflt") == 0
    assert c.hits == 1


def test_hit_and_miss_counters():
    """Hits and misses are counted per lookup"""
    c = LRUCache(2)
    c.get("x")
    c.put("x", 1)
    c.get("x")
    c.get("x")
    c.get("y")
    assert (c.hits, c.misses) == (2, 2)


def test_hit_rate():
    """Hit rate is hits divided by lookups, or 0.0 before any lookup"""
    c = LRUCache(2)
    assert c.hit_rate() == 0.0
    c.put("a", 1)
    c.get("a")
    c.get("b")
    assert c.hit_rate() == pytest.approx(0.5)
    c.get("a")
    c.get("a")
    assert c.hit_rate() == pytest.approx(0.75)


def test_without_ttl_entries_never_expire():
    """Entries live forever when no ttl is configured"""
    clock = Clock()
    c = LRUCache(2, clock=clock)
    c.put("a", 1)
    clock.advance(1e9)
    assert c.get("a") == 1


def test_ttl_expiry_boundary():
    """An entry is valid just before its ttl elapses and expired exactly at it"""
    clock = Clock()
    c = LRUCache(2, ttl=10, clock=clock)
    c.put("a", 1)
    clock.advance(9)
    assert c.get("a") == 1
    clock.advance(1)
    assert c.get("a") is None


def test_expired_lookup_counts_as_miss_and_removes_entry():
    """Reading an expired entry is a miss and drops it"""
    clock = Clock()
    c = LRUCache(2, ttl=5, clock=clock)
    c.put("a", 1)
    clock.advance(6)
    assert c.get("a", "gone") == "gone"
    assert (c.hits, c.misses) == (0, 1)
    assert len(c) == 0


def test_put_resets_ttl():
    """Writing a key again restarts its time-to-live"""
    clock = Clock()
    c = LRUCache(2, ttl=10, clock=clock)
    c.put("a", 1)
    clock.advance(6)
    c.put("a", 2)
    clock.advance(6)
    assert c.get("a") == 2


def test_get_does_not_reset_ttl():
    """Reading an entry does not extend its time-to-live"""
    clock = Clock()
    c = LRUCache(2, ttl=10, clock=clock)
    c.put("a", 1)
    clock.advance(6)
    assert c.get("a") == 1
    clock.advance(5)
    assert c.get("a") is None


def test_purge_returns_number_removed():
    """Purge removes every expired entry and reports how many"""
    clock = Clock()
    c = LRUCache(5, ttl=5, clock=clock)
    c.put("a", 1)
    clock.advance(3)
    c.put("b", 2)
    clock.advance(3)
    c.put("c", 3)
    clock.advance(2)
    assert c.purge() == 2
    assert len(c) == 1
    assert c.get("c") == 3


def test_len_ignores_expired_entries():
    """Expired entries do not count towards the length"""
    clock = Clock()
    c = LRUCache(3, ttl=5, clock=clock)
    c.put("a", 1)
    c.put("b", 2)
    assert len(c) == 2
    clock.advance(5)
    assert len(c) == 0


def test_bucket_allows_burst_then_denies():
    """A full bucket allows `burst` requests and then denies"""
    b = TokenBucket(rate=1, burst=3, clock=Clock())
    assert [b.allow() for _ in range(4)] == [True, True, True, False]


def test_bucket_refills_over_time():
    """Tokens come back at `rate` per second"""
    clock = Clock()
    b = TokenBucket(rate=1, burst=3, clock=clock)
    for _ in range(3):
        b.allow()
    clock.advance(1)
    assert b.allow() is True
    assert b.allow() is False


def test_bucket_never_exceeds_burst():
    """Idle time cannot bank more than `burst` tokens"""
    clock = Clock()
    b = TokenBucket(rate=1, burst=3, clock=clock)
    clock.advance(100)
    assert [b.allow() for _ in range(4)] == [True, True, True, False]


def test_bucket_cost():
    """Requests can cost more than one token"""
    b = TokenBucket(rate=1, burst=3, clock=Clock())
    assert b.allow(cost=2) is True
    assert b.allow(cost=2) is False
    assert b.allow() is True


def test_bucket_denied_request_consumes_nothing():
    """A denied request leaves the tokens untouched"""
    b = TokenBucket(rate=1, burst=2, clock=Clock())
    assert b.allow(cost=3) is False
    assert b.allow(cost=2) is True


def test_bucket_fractional_refill():
    """Partial tokens accumulate until a whole token is available"""
    clock = Clock()
    b = TokenBucket(rate=2, burst=1, clock=clock)
    assert b.allow() is True
    clock.advance(0.25)
    assert b.allow() is False
    clock.advance(0.25)
    assert b.allow() is True


def test_bucket_wait_time():
    """wait_time reports how long until a request would be allowed"""
    clock = Clock()
    b = TokenBucket(rate=2, burst=1, clock=clock)
    assert b.wait_time() == 0.0
    b.allow()
    assert b.wait_time() == pytest.approx(0.5)
    clock.advance(0.25)
    assert b.wait_time() == pytest.approx(0.25)


def test_bucket_wait_time_for_larger_cost():
    """wait_time accounts for the cost of the request"""
    b = TokenBucket(rate=1, burst=5, clock=Clock())
    b.allow(cost=5)
    assert b.wait_time(cost=3) == pytest.approx(3.0)
