"""
簡單的記憶體快取系統
用於快取 API 響應以提升性能
"""
import time
from typing import Any, Optional, Callable
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

class SimpleCache:
    """簡單的記憶體快取實現"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取值"""
        if key in self._cache:
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """設置快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl: 過期時間（秒），預設 5 分鐘
        """
        self._cache[key] = value
        self._timestamps[key] = time.time() + ttl
    
    def delete(self, key: str):
        """刪除快取值"""
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
    
    def clear(self):
        """清空所有快取"""
        self._cache.clear()
        self._timestamps.clear()
    
    def cleanup(self):
        """清理過期的快取項"""
        current_time = time.time()
        expired_keys = [
            key for key, expire_time in self._timestamps.items()
            if current_time > expire_time
        ]
        for key in expired_keys:
            self.delete(key)
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def invalidate_pattern(self, pattern: str):
        """刪除匹配模式的所有快取"""
        keys_to_delete = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_delete:
            self.delete(key)
        
        if keys_to_delete:
            logger.debug(f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")

# 全局快取實例
_cache_instance = SimpleCache()

def get_cache() -> SimpleCache:
    """獲取全局快取實例"""
    return _cache_instance

def cache_response(ttl: int = 300, key_prefix: str = ""):
    """
    API 響應快取裝飾器
    
    Args:
        ttl: 快取過期時間（秒）
        key_prefix: 快取鍵前綴
    
    Example:
        @cache_response(ttl=300, key_prefix="statistics")
        async def get_statistics():
            # ... expensive operation
            return result
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成快取鍵
            cache_key = _generate_cache_key(func.__name__, key_prefix, args, kwargs)
            
            # 檢查快取
            cache = get_cache()
            cache.cleanup()  # 定期清理過期項
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            # 執行函數
            logger.debug(f"Cache miss for {cache_key}")
            result = await func(*args, **kwargs)
            
            # 儲存到快取
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def _generate_cache_key(func_name: str, prefix: str, args: tuple, kwargs: dict) -> str:
    """生成快取鍵"""
    # 過濾掉 db session 等不可序列化的參數
    filtered_kwargs = {
        k: v for k, v in kwargs.items() 
        if not k in ['db', 'current_user'] and _is_serializable(v)
    }
    
    # 創建鍵的基礎部分
    key_parts = [prefix, func_name]
    
    # 添加參數的哈希值
    if args or filtered_kwargs:
        try:
            param_str = json.dumps({
                'args': [str(a) for a in args if _is_serializable(a)],
                'kwargs': filtered_kwargs
            }, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        except (TypeError, ValueError):
            # 如果無法序列化，使用時間戳確保唯一性
            key_parts.append(str(time.time()))
    
    return ":".join(filter(None, key_parts))

def _is_serializable(value: Any) -> bool:
    """檢查值是否可序列化"""
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False

# 快取失效工具函數
def invalidate_cache(pattern: str = ""):
    """使快取失效
    
    Args:
        pattern: 要失效的快取鍵模式，留空則清空所有快取
    """
    cache = get_cache()
    if pattern:
        cache.invalidate_pattern(pattern)
    else:
        cache.clear()
