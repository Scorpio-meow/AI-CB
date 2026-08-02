
import redis
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
import os
logger = logging.getLogger(__name__)
class RedisCache:
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "7967"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.enabled = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
        
        self.default_ttl = int(os.getenv("CACHE_TTL_SECONDS", "300"))
        self.prefix = "chatbot:rag:"
        
        self.client = None
        
        if self.enabled:
            try:
                self.client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                self.client.ping()
                logger.info(f"Redis 快取已啟用: {self.host}:{self.port}/{self.db}")
            except Exception as e:
                logger.warning(f"Redis 連線失敗，快取已禁用: {e}")
                self.client = None
                self.enabled = False
        else:
            logger.info("Redis 快取已禁用 (設定 ENABLE_REDIS_CACHE=true 啟用)")
    
    def _make_cache_key(self, query: str, user_id: Optional[int] = None, 
                       conversation_id: Optional[int] = None) -> str:
        normalized = query.strip().lower()
        
        hash_input = f"{normalized}:{user_id}:{conversation_id}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        return f"{self.prefix}query:{hash_value}"
    
    def get(self, query: str, user_id: Optional[int] = None, 
           conversation_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.client:
            return None
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            cached = self.client.get(key)
            
            if cached:
                result = json.loads(cached)
                logger.info(f"快取命中: {key}")
                return result
            
            logger.debug(f"快取未命中: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Redis GET 錯誤: {e}")
            return None
    
    def set(self, query: str, result: Dict[str, Any], 
           user_id: Optional[int] = None, 
           conversation_id: Optional[int] = None,
           ttl: Optional[int] = None) -> bool:
        if not self.enabled or not self.client:
            return False
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            value = json.dumps(result, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            
            self.client.setex(key, ttl, value)
            logger.debug(f"快取已儲存: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis SET 錯誤: {e}")
            return False
    
    def delete(self, query: str, user_id: Optional[int] = None,
              conversation_id: Optional[int] = None) -> bool:
        if not self.enabled or not self.client:
            return False
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            result = self.client.delete(key)
            logger.debug(f"快取已刪除: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis DELETE 錯誤: {e}")
            return False
    
    def clear_all(self) -> int:
        if not self.enabled or not self.client:
            return 0
        
        try:
            pattern = f"{self.prefix}*"
            keys = self.client.keys(pattern)
            
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"已清空 {count} 個快取項目")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Redis CLEAR 錯誤: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.enabled or not self.client:
            return {
                "enabled": False,
                "message": "Redis cache is disabled"
            }
        
        try:
            info = self.client.info("stats")
            pattern = f"{self.prefix}*"
            cache_keys = self.client.keys(pattern)
            
            return {
                "enabled": True,
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "total_cache_keys": len(cache_keys),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
                "default_ttl": self.default_ttl
            }
            
        except Exception as e:
            logger.error(f"Redis STATS 錯誤: {e}")
            return {
                "enabled": False,
                "error": str(e)
            }
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)
    
    def invalidate_pattern(self, pattern: str) -> int:
        if not self.enabled or not self.client:
            return 0
        
        try:
            full_pattern = f"{self.prefix}{pattern}"
            keys = self.client.keys(full_pattern)
            
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"模式 '{pattern}' 刪除 {count} 個快取")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Redis INVALIDATE 錯誤: {e}")
            return 0
_cache_instance = None
def get_cache() -> RedisCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
