"""
Redis 客戶端配置
用於 Token 黑名單和快取管理
"""

import os
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Redis 配置
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Redis 連接池
redis_pool = None
redis_client = None


def init_redis():
    """初始化 Redis 連接"""
    global redis_pool, redis_client
    
    try:
        redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
            max_connections=10
        )
        
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # 測試連接
        redis_client.ping()
        print(f"✅ Redis 連接成功: {REDIS_HOST}:{REDIS_PORT}")
        return True
    except redis.ConnectionError as e:
        print(f"⚠️  Redis 連接失敗: {e}")
        print("⚠️  Token 黑名單功能將不可用，但系統仍可正常運行")
        redis_client = None
        return False
    except Exception as e:
        print(f"⚠️  Redis 初始化錯誤: {e}")
        redis_client = None
        return False


def get_redis() -> Optional[redis.Redis]:
    """獲取 Redis 客戶端"""
    global redis_client
    
    if redis_client is None:
        init_redis()
    
    return redis_client


def close_redis():
    """關閉 Redis 連接"""
    global redis_client, redis_pool
    
    if redis_client:
        redis_client.close()
        redis_client = None
    
    if redis_pool:
        redis_pool.disconnect()
        redis_pool = None


class TokenBlacklist:
    """Token 黑名單管理器"""
    
    PREFIX = "blacklist:token:"
    
    @staticmethod
    def add_token(token: str, expires_in: int = 3600):
        """
        將 token 加入黑名單
        
        Args:
            token: JWT token
            expires_in: 過期時間（秒）
        """
        client = get_redis()
        if client is None:
            print("⚠️  Redis 不可用，無法加入黑名單")
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            client.setex(key, expires_in, "revoked")
            return True
        except Exception as e:
            print(f"❌ 加入黑名單失敗: {e}")
            return False
    
    @staticmethod
    def is_blacklisted(token: str) -> bool:
        """
        檢查 token 是否在黑名單中
        
        Args:
            token: JWT token
            
        Returns:
            bool: True 如果在黑名單中
        """
        client = get_redis()
        if client is None:
            # Redis 不可用時，假設 token 有效
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            return client.exists(key) > 0
        except Exception as e:
            print(f"❌ 檢查黑名單失敗: {e}")
            # 發生錯誤時，為安全起見，假設 token 有效
            return False
    
    @staticmethod
    def remove_token(token: str):
        """
        從黑名單移除 token (主要用於測試)
        
        Args:
            token: JWT token
        """
        client = get_redis()
        if client is None:
            return False
        
        try:
            key = f"{TokenBlacklist.PREFIX}{token}"
            client.delete(key)
            return True
        except Exception as e:
            print(f"❌ 移除黑名單失敗: {e}")
            return False


# 初始化 Redis（啟動時）
init_redis()
