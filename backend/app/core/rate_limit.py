from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP, in-memory (no Redis) - this is a single-process self-hosted deploy, not a multi-worker
# cluster, so in-memory state is correct here (a Redis-backed store would only matter if traffic
# were ever split across multiple backend processes). Shared module so both main.py (registers the
# exception handler) and individual route files (apply @limiter.limit(...) per endpoint) import
# the same instance - slowapi tracks hit counts on the Limiter object itself.
limiter = Limiter(key_func=get_remote_address)
