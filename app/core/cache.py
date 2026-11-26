import hashlib
import json
import redis
from app.core.config import get_settings

settings = get_settings()

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


CACHE_TTL_SECONDS = 1800


def build_cache_key(
    tenant_id: str,
    user_role: str,
    user_groups: list[str],
    query: str,
) -> str:
    """Create a unique, security-scoped SHA-256 key for this user's permissions + query."""
    normalized_query = " ".join(query.strip().lower().split())
    sorted_groups = ",".join(sorted(user_groups))
    raw_key = f"{tenant_id}|{user_role}|{sorted_groups}|{normalized_query}"
    hashed = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return f"rag_cache:{hashed}"


def get_cached_response(
    tenant_id: str,
    user_role: str,
    user_groups: list[str],
    query: str,
) -> dict | None:
    """Return the cached response dict if it exists, otherwise None."""
    key = build_cache_key(tenant_id, user_role, user_groups, query)
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except redis.RedisError as exc:
        # Fail gracefully: if Redis is temporarily unavailable, just skip cache
        print(f"[Cache Warning] Redis read failed: {exc}")
    return None


def set_cached_response(
    tenant_id: str,
    user_role: str,
    user_groups: list[str],
    query: str,
    data: dict,
) -> None:
    """Save the response in Redis with an expiration timer (TTL)."""
    key = build_cache_key(tenant_id, user_role, user_groups, query)
    try:
        redis_client.setex(key, CACHE_TTL_SECONDS, json.dumps(data))
    except redis.RedisError as exc:
        print(f"[Cache Warning] Redis write failed: {exc}")