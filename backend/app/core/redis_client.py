
import os
import redis
from typing import Optional
from dotenv import load_dotenv
load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "7967"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
redis_pool = None
redis_client = None
def init_redis():
    global redis_pool, redis_client
    
    try:
        redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            max_connections=10,
            socket_connect_timeout=0.5,
            socket_timeout=0.5
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        redis_client.ping()
        print(f"Redis 連接成功: {REDIS_HOST}:{REDIS_PORT}")
        print(f"Token 黑名單功能已啟用")
        return True
    except redis.ConnectionError as e:
        print(f"Redis 連接失敗: {e}")
        print("Token 黑名單功能將不可用，但系統仍可正常運行")
        redis_client = None
        return False
    except Exception as e:
        print(f"Redis 初始化錯誤: {e}")
        redis_client = None
        return False
def get_redis() -> Optional[redis.Redis]:
    global redis_client
    
    if redis_client is None:
        init_redis()
    
    return redis_client
def close_redis():
    global redis_client, redis_pool
    
    if redis_client:
        redis_client.close()
        redis_client = None
    
    if redis_pool:
        redis_pool.disconnect()
        redis_pool = None
class TokenBlacklist:
    
    PREFIX = "blacklist:token:"
    
    @staticmethod
    def add_token(token: str, expires_in: int = 3600):
        client = get_redis()
        if client is None:
            print("Redis 不可用，無法加入黑名單")
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            client.setex(key, expires_in, "revoked")
            return True
        except Exception as e:
            print(f"加入黑名單失敗: {e}")
            return False
    
    @staticmethod
    def is_blacklisted(token: str) -> bool:
        client = get_redis()
        if client is None:
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            return client.exists(key) > 0
        except Exception as e:
            print(f"檢查黑名單失敗: {e}")
            return False
    
    @staticmethod
    def remove_token(token: str):
        client = get_redis()
        if client is None:
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            client.delete(key)
            return True
        except Exception as e:
            print(f"移除黑名單失敗: {e}")
            return False
init_redis()
