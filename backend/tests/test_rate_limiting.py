"""Rate limiting on the public, unauthenticated signup/login endpoints - added once the app went
live and public, since these previously had no protection against signup spam or credential
stuffing. The limiter is disabled globally in conftest.py (see its comment) since it's a
module-level singleton shared across every test's TestClient; re-enabled here just long enough to
verify it actually blocks, then restored so it doesn't leak into other tests."""
import pytest

from app.core.rate_limit import limiter


@pytest.fixture
def rate_limiting_enabled():
    limiter.enabled = True
    limiter.reset()
    yield
    limiter.enabled = False


def test_login_rate_limit_blocks_after_threshold(client, rate_limiting_enabled):
    payload = {"email": "nobody@example.com", "password": "wrong"}

    for _ in range(10):
        response = client.post("/auth/login", json=payload)
        assert response.status_code != 429

    blocked = client.post("/auth/login", json=payload)
    assert blocked.status_code == 429


def test_school_register_rate_limit_blocks_after_threshold(client, rate_limiting_enabled):
    payload = {
        "code": "RLT", "name": "Rate Limit Test School", "slug": "rate-limit-test-school",
        "username": "ratelimittestadmin", "email": "ratelimittest@example.com",
        "password": "TestPass123!", "first_name": "A", "last_name": "B",
    }

    for _ in range(3):
        client.post("/schools/register", json=payload)

    blocked = client.post("/schools/register", json=payload)
    assert blocked.status_code == 429
