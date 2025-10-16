"""
Security middleware and authentication utilities
"""
import os
import secrets
from typing import Optional
from fastapi import Header, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from app.core.security_logging import log_unauthorized_access, log_security_event, SecurityEvent

logger = logging.getLogger(__name__)

# Security bearer scheme
security = HTTPBearer()

# Admin API Key from environment
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

if not ADMIN_API_KEY or ADMIN_API_KEY == "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING":
    # Generate a temporary secure key for development
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.warning("=" * 80)
    logger.warning("⚠️  WARNING: ADMIN_API_KEY not set in environment!")
    logger.warning(f"⚠️  Using temporary API key: {ADMIN_API_KEY}")
    logger.warning("⚠️  Please set ADMIN_API_KEY in your .env file!")
    logger.warning("=" * 80)


async def verify_admin_api_key(x_api_key: Optional[str] = Header(None, description="Admin API Key")) -> bool:
    """
    驗證管理員 API Key
    
    Args:
        x_api_key: API Key from X-API-Key header
        
    Returns:
        bool: True if valid
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not x_api_key:
        logger.warning("Admin API access attempt without API key")
        # 此處無法獲取 Request 對象，在路由層記錄
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    if x_api_key != ADMIN_API_KEY:
        logger.warning(f"Admin API access attempt with invalid API key: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # 成功驗證時記錄
    logger.info("Admin API access granted")
    return True


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    添加安全相關的 HTTP Headers
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove server information (use del instead of pop for MutableHeaders)
        if "Server" in response.headers:
            del response.headers["Server"]
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    增強的速率限制中間件（帶入侵檢測）
    """
    def __init__(self, app, calls: int = 60, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
        
    async def dispatch(self, request: Request, call_next):
        # 獲取客戶端 IP
        client_ip = request.client.host
        
        # 導入入侵檢測系統
        try:
            from app.core.intrusion_detection import get_intrusion_detector
            detector = get_intrusion_detector()
            
            # 檢查黑名單
            if detector.is_blacklisted(client_ip):
                logger.error(f"🚫 拒絕黑名單 IP 訪問: {client_ip}")
                return Response(
                    content="Access Denied. Your IP has been blacklisted due to suspicious activity.",
                    status_code=403
                )
        except Exception as e:
            logger.debug(f"入侵檢測系統不可用: {e}")
            detector = None
        
        # 檢查速率限制
        import time
        current_time = time.time()
        
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        
        # 清理過期的請求記錄
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if current_time - req_time < self.period
        ]
        
        # 檢查是否超過限制
        if len(self.clients[client_ip]) >= self.calls:
            logger.warning(f"⚠️ 速率限制: {client_ip} 超過限制 ({len(self.clients[client_ip])} requests)")
            
            # 記錄到入侵檢測系統
            if detector:
                detector.record_event(
                    'api_request',
                    client_ip,
                    details={'rate_limit_exceeded': True}
                )
            
            return Response(
                content="Rate limit exceeded. Please try again later.",
                status_code=429,
                headers={"Retry-After": str(self.period)}
            )
        
        # 記錄此次請求
        self.clients[client_ip].append(current_time)
        
        # 記錄正常的 API 請求（用於監控）
        if detector and len(self.clients[client_ip]) % 10 == 0:  # 每 10 個請求記錄一次
            detector.record_event('api_request', client_ip)
        
        response = await call_next(request)
        return response


def validate_api_endpoint(url: str) -> str:
    """
    驗證 API 端點 URL 的安全性
    
    Args:
        url: API endpoint URL
        
    Returns:
        str: Validated URL
        
    Raises:
        ValueError: If URL is insecure
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # 在生產環境中禁止使用 ngrok
    if os.getenv("ENVIRONMENT") == "production" and "ngrok" in parsed.netloc:
        raise ValueError(
            "Ngrok URLs are not allowed in production environment. "
            "Please use a proper domain name."
        )
    
    # 確保使用 HTTPS（生產環境）
    if os.getenv("ENVIRONMENT") == "production" and parsed.scheme != "https":
        logger.warning(f"Using non-HTTPS URL in production: {url}")
    
    return url
