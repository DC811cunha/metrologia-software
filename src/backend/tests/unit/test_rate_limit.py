import asyncio

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import rate_limit
from app.core.rate_limit import MemoryRateLimiter, RedisRateLimiter, rule_for


def run(coro):
    return asyncio.run(coro)


class TestRuleFor:
    def test_login_and_password_recovery_are_always_limited(self):
        for path in (
            "/api/v1/auth/login",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
        ):
            rule = rule_for("POST", path)
            assert rule is not None
            assert (rule.limit, rule.window_s) == (10, 60)

    def test_only_post_is_limited(self):
        assert rule_for("GET", "/api/v1/auth/login") is None

    def test_other_routes_are_not_limited(self):
        assert rule_for("POST", "/api/v1/repositories") is None

    def test_extended_rules_apply_only_in_production(self, monkeypatch):
        monkeypatch.setattr(rate_limit.settings, "environment", "development")
        assert rule_for("POST", "/api/v1/auth/register") is None

        monkeypatch.setattr(rate_limit.settings, "environment", "production")
        register = rule_for("POST", "/api/v1/auth/register")
        analyses = rule_for("POST", "/api/v1/repositories/abc/analyses")
        assert register is not None and (register.limit, register.window_s) == (10, 3600)
        assert analyses is not None and (analyses.limit, analyses.window_s) == (20, 3600)

    def test_analyses_rule_is_shared_by_all_repositories(self, monkeypatch):
        monkeypatch.setattr(rate_limit.settings, "environment", "production")

        a = rule_for("POST", "/api/v1/repositories/aaa/analyses")
        b = rule_for("POST", "/api/v1/repositories/bbb/analyses")

        assert a is not None and b is not None and a.name == b.name


class TestMemoryRateLimiter:
    def test_allows_up_to_the_limit_then_reports_retry_after(self):
        limiter = MemoryRateLimiter()

        results = [run(limiter.hit("k", 3, 60)) for _ in range(4)]

        assert results[:3] == [None, None, None]
        assert results[3] is not None and 1 <= results[3] <= 60

    def test_keys_are_independent(self):
        limiter = MemoryRateLimiter()
        for _ in range(3):
            run(limiter.hit("a", 3, 60))

        assert run(limiter.hit("a", 3, 60)) is not None
        assert run(limiter.hit("b", 3, 60)) is None

    def test_idle_keys_are_swept_so_memory_does_not_grow(self, monkeypatch):
        limiter = MemoryRateLimiter()
        clock = {"now": 1000.0}
        monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock["now"])
        limiter._last_sweep = clock["now"]

        for index in range(50):
            run(limiter.hit(f"ip-{index}", 10, 60))
        assert len(limiter) == 50

        clock["now"] += 200  # janelas expiradas e intervalo de varredura vencido
        run(limiter.hit("fresh", 10, 60))

        assert len(limiter) == 1

    def test_window_slides(self, monkeypatch):
        limiter = MemoryRateLimiter()
        clock = {"now": 1000.0}
        monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock["now"])

        run(limiter.hit("k", 1, 60))
        assert run(limiter.hit("k", 1, 60)) is not None

        clock["now"] += 61
        assert run(limiter.hit("k", 1, 60)) is None


class FakeRedis:
    def __init__(self):
        self.counters: dict[str, int] = {}
        self.expirations: dict[str, int] = {}

    async def incr(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
        return self.counters[key]

    async def expire(self, key, seconds):
        self.expirations[key] = seconds


def redis_limiter(client, fallback=None):
    limiter = RedisRateLimiter("redis://localhost:6379/0", fallback or MemoryRateLimiter())
    limiter._client = client
    return limiter


class TestRedisRateLimiter:
    def test_counts_in_redis_and_sets_expiry_only_on_the_first_hit(self):
        fake = FakeRedis()
        limiter = redis_limiter(fake)

        results = [run(limiter.hit("login:1.2.3.4", 2, 60)) for _ in range(3)]

        assert results[:2] == [None, None]
        assert results[2] is not None and 1 <= results[2] <= 60
        assert len(fake.counters) == 1
        assert list(fake.expirations.values()) == [60]

    def test_state_is_shared_between_limiter_instances(self):
        fake = FakeRedis()
        first, second = redis_limiter(fake), redis_limiter(fake)

        run(first.hit("k", 1, 60))

        assert run(second.hit("k", 1, 60)) is not None

    def test_falls_back_to_memory_when_redis_is_down(self, caplog):
        class Broken:
            async def incr(self, key):
                raise RedisConnectionError("down")

        limiter = redis_limiter(Broken())

        results = [run(limiter.hit("k", 1, 60)) for _ in range(2)]

        assert results[0] is None
        assert results[1] is not None
        assert "Redis indisponível" in caplog.text

    @pytest.mark.parametrize("backend", ["memory", "redis"])
    def test_get_rate_limiter_follows_the_configured_backend(self, backend, monkeypatch):
        monkeypatch.setattr(rate_limit.settings, "rate_limit_backend", backend)
        rate_limit.reset_rate_limits()

        limiter = rate_limit.get_rate_limiter()

        assert isinstance(limiter, RedisRateLimiter if backend == "redis" else MemoryRateLimiter)
        rate_limit.reset_rate_limits()
