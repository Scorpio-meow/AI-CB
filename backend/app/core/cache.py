
import time
from typing import Any, Optional, Callable
from functools import wraps
import hashlib
import json
import logging
logger = logging.getLogger(__name__)
class SimpleCache:
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        self._cache[key] = value
        self._timestamps[key] = time.time() + ttl
    
    def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]
        if key in self._timestamps:
            del self._timestamps[key]
    
    def clear(self):
        self._cache.clear()
        self._timestamps.clear()
    
    def cleanup(self):
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
        keys_to_delete = [key for key in self._cache.keys() if pattern in key]
        for key in keys_to_delete:
            self.delete(key)
        
        if keys_to_delete:
            logger.debug(f"Invalidated {len(keys_to_delete)} cache entries matching '{pattern}'")
_cache_instance = SimpleCache()
def get_cache() -> SimpleCache:
    return _cache_instance
def cache_response(ttl: int = 300, key_prefix: str = ""):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(func.__name__, key_prefix, args, kwargs)
            
            cache = get_cache()
            cache.cleanup()
            
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_value
            
            logger.debug(f"Cache miss for {cache_key}")
            result = await func(*args, **kwargs)
            
            cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
def _generate_cache_key(func_name: str, prefix: str, args: tuple, kwargs: dict) -> str:
    filtered_kwargs = {
        k: v for k, v in kwargs.items() 
        if not k in ['db', 'current_user'] and _is_serializable(v)
    }
    
    key_parts = [prefix, func_name]
    
    if args or filtered_kwargs:
        try:
            param_str = json.dumps({
                'args': [str(a) for a in args if _is_serializable(a)],
                'kwargs': filtered_kwargs
            }, sort_keys=True)
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
            key_parts.append(param_hash)
        except (TypeError, ValueError):
            key_parts.append(str(time.time()))
    
    return ":".join(filter(None, key_parts))
def _is_serializable(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
def invalidate_cache(pattern: str = ""):
    cache = get_cache()
    if pattern:
        cache.invalidate_pattern(pattern)
    else:
        cache.clear()
