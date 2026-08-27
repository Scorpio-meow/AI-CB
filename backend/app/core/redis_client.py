import time
import logging
import threading
from typing import Dict, Optional
logger = logging.getLogger(__name__)
class TokenBlacklist:
    """記憶體型 Token 黑名單管理器（無須外部 Redis 依賴）"""
    _blacklist: Dict[str, float] = {}
    _lock = threading.Lock()
    @classmethod
    def _cleanup_expired(cls):
        now = time.time()
        expired = [t for t, exp in cls._blacklist.items() if exp <= now]
        for t in expired:
            del cls._blacklist[t]
    @classmethod
    def add_token(cls, token: str, expires_in: int = 3600) -> bool:
        try:
            with cls._lock:
                cls._cleanup_expired()
                cls._blacklist[token] = time.time() + max(1, expires_in)
            return True
        except Exception as e:
            logger.error(f"加入黑名單失敗: {e}")
            return False
    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        try:
            with cls._lock:
                cls._cleanup_expired()
                if token in cls._blacklist:
                    if cls._blacklist[token] > time.time():
                        return True
                    else:
                        del cls._blacklist[token]
            return False
        except Exception as e:
            logger.error(f"檢查黑名單失敗: {e}")
            return False
    @classmethod
    def remove_token(cls, token: str) -> bool:
        try:
            with cls._lock:
                if token in cls._blacklist:
                    del cls._blacklist[token]
            return True
        except Exception as e:
            logger.error(f"移除黑名單失敗: {e}")
            return False
def init_redis():
    """向下相容保留，直接回傳 True"""
    logger.info("Token 黑名單已採用記憶體模式運行 (無需 Redis)")
    return True
def get_redis() -> Optional[object]:
    """向下相容保留"""
    return None
def close_redis():
    """向下相容保留"""
    pass
