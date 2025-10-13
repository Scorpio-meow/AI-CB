"""
Redis 快取服務 - 用於加速 RAG 檢索結果
支援查詢結果快取、自動過期、批次清理
"""
import redis
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List
from datetime import timedelta
import os

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis 快取管理器"""
    
    def __init__(self):
        # Redis 連線配置
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", "6379"))
        self.db = int(os.getenv("REDIS_DB", "0"))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.enabled = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"
        
        # 快取配置
        self.default_ttl = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5分鐘
        self.prefix = "chatbot:rag:"
        
        # Redis 客戶端
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
                # 測試連線
                self.client.ping()
                logger.info(f"✅ Redis 快取已啟用: {self.host}:{self.port}/{self.db}")
            except Exception as e:
                logger.warning(f"⚠️ Redis 連線失敗，快取已禁用: {e}")
                self.client = None
                self.enabled = False
        else:
            logger.info("Redis 快取已禁用 (設定 ENABLE_REDIS_CACHE=true 啟用)")
    
    def _make_cache_key(self, query: str, user_id: Optional[int] = None, 
                       conversation_id: Optional[int] = None) -> str:
        """生成快取鍵 (基於查詢內容雜湊)"""
        # 標準化查詢文本
        normalized = query.strip().lower()
        
        # 生成雜湊 (包含用戶和對話上下文)
        hash_input = f"{normalized}:{user_id}:{conversation_id}"
        hash_value = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        return f"{self.prefix}query:{hash_value}"
    
    def get(self, query: str, user_id: Optional[int] = None, 
           conversation_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """獲取快取的查詢結果"""
        if not self.enabled or not self.client:
            return None
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            cached = self.client.get(key)
            
            if cached:
                result = json.loads(cached)
                logger.info(f"🎯 快取命中: {key}")
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
        """儲存查詢結果到快取"""
        if not self.enabled or not self.client:
            return False
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            value = json.dumps(result, ensure_ascii=False)
            ttl = ttl or self.default_ttl
            
            self.client.setex(key, ttl, value)
            logger.debug(f"💾 快取已儲存: {key} (TTL: {ttl}s)")
            return True
            
        except Exception as e:
            logger.error(f"Redis SET 錯誤: {e}")
            return False
    
    def delete(self, query: str, user_id: Optional[int] = None,
              conversation_id: Optional[int] = None) -> bool:
        """刪除特定查詢的快取"""
        if not self.enabled or not self.client:
            return False
        
        try:
            key = self._make_cache_key(query, user_id, conversation_id)
            result = self.client.delete(key)
            logger.debug(f"🗑️ 快取已刪除: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Redis DELETE 錯誤: {e}")
            return False
    
    def clear_all(self) -> int:
        """清空所有 RAG 快取"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            pattern = f"{self.prefix}*"
            keys = self.client.keys(pattern)
            
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"🧹 已清空 {count} 個快取項目")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Redis CLEAR 錯誤: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取快取統計資訊"""
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
        """計算快取命中率"""
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式批次刪除快取"""
        if not self.enabled or not self.client:
            return 0
        
        try:
            full_pattern = f"{self.prefix}{pattern}"
            keys = self.client.keys(full_pattern)
            
            if keys:
                count = self.client.delete(*keys)
                logger.info(f"🗑️ 模式 '{pattern}' 刪除 {count} 個快取")
                return count
            
            return 0
            
        except Exception as e:
            logger.error(f"Redis INVALIDATE 錯誤: {e}")
            return 0

# 全域快取實例
_cache_instance = None

def get_cache() -> RedisCache:
    """獲取全域快取實例 (單例模式)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance
