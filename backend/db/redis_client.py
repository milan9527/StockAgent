"""
Redis缓存客户端 - 行情缓存、会话缓存、信号队列
ElastiCache Serverless requires TLS
"""
import json
from typing import Any, Optional
import redis.asyncio as aioredis
from config.settings import get_settings

settings = get_settings()

# ElastiCache Serverless requires TLS
_use_ssl = settings.ENV.value == "aws"

if _use_ssl:
    redis_client = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD or None,
        ssl=True,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
else:
    redis_pool = aioredis.ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=20,
        decode_responses=True,
    )
    redis_client = aioredis.Redis(connection_pool=redis_pool)


# ── 缓存Key前缀 ──
class CacheKeys:
    STOCK_QUOTE = "quote:{code}"
    STOCK_KLINE = "kline:{code}:{period}"
    STOCK_LIST = "stock:list:{market}"
    USER_SESSION = "session:{user_id}"
    SIGNAL_QUEUE = "signals:queue"
    AGENT_CONTEXT = "agent:ctx:{session}"


async def cache_get(key: str) -> Optional[Any]:
    """获取缓存 (Redis失败时返回None，不阻塞)"""
    try:
        data = await redis_client.get(key)
        if data:
            try:
                return json.loads(data)
            except (json.JSONDecodeError, TypeError):
                return data
    except Exception as e:
        # Redis connection error — skip cache silently
        pass
    return None


async def cache_set(key: str, value: Any, ttl: int = 60):
    """设置缓存 (Redis失败时静默跳过)"""
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await redis_client.set(key, value, ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str):
    """删除缓存"""
    try:
        await redis_client.delete(key)
    except Exception:
        pass


async def push_signal(signal_data: dict):
    """推送交易信号到队列"""
    try:
        await redis_client.lpush(
            CacheKeys.SIGNAL_QUEUE,
            json.dumps(signal_data, ensure_ascii=False, default=str)
        )
    except Exception:
        pass


async def pop_signal() -> Optional[dict]:
    """从队列获取交易信号"""
    try:
        data = await redis_client.rpop(CacheKeys.SIGNAL_QUEUE)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None
