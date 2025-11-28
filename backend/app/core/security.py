import os
import secrets
import hashlib
import hmac
from typing import Optional
from fastapi import Header, HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import logging
from app.core.security_logging import log_unauthorized_access, log_security_event, SecurityEvent
logger = logging.getLogger(__name__)
security = HTTPBearer()
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
_digest_salt = b"cb_api_key_salt"
# 安全註解：
# 下方 HMAC-SHA256 雜湊僅用於 API Key 日誌辨識（不可逆），不作為密碼雜湊或敏感資料存儲。
# 不涉及驗證或存儲用途，無弱雜湊攻擊風險，符合 OWASP/CodeQL 建議。
if not ADMIN_API_KEY or ADMIN_API_KEY == "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING":
    # Generate a temporary secure key for development
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.warning("=" * 80)
    logger.warning("⚠️  WARNING: ADMIN_API_KEY not set in environment!")
    try:
        # 僅用於日誌辨識，不作密碼雜湊
        digest = hmac.new(_digest_salt, ADMIN_API_KEY.encode('utf-8'), hashlib.sha256).hexdigest()[:8]
    except Exception:
        digest = 'unknown'
    logger.warning("⚠️  Using temporary API key (digest): %s", digest)
    logger.warning("⚠️  Please set ADMIN_API_KEY in your .env file!")
    logger.warning("=" * 80)
async def verify_admin_api_key(x_api_key: Optional[str] = Header(None, description="Admin API Key")) -> bool:
    if not x_api_key:
        logger.warning("Admin API access attempt without API key")
        # 此處無法獲取 Request 對象，在路由層記錄
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    if x_api_key != ADMIN_API_KEY:
        # 僅用於日誌辨識，不作密碼雜湊
        # Do not log the raw key value. Log a non-reversible digest to help operators identify attempts.
        try:
            digest = hmac.new(_digest_salt, x_api_key.encode('utf-8'), hashlib.sha256).hexdigest()[:8]
        except Exception:
            digest = 'unknown'
        logger.warning("Admin API access attempt with invalid API key (digest): %s", digest)
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    logger.info("Admin API access granted")
    return True
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if "Server" in response.headers:
            del response.headers["Server"]
        return response
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls: int = 60, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients = {}
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        try:
            from app.core.intrusion_detection import get_intrusion_detector
            detector = get_intrusion_detector()
            if detector.is_blacklisted(client_ip):
                logger.error(f"🚫 拒絕黑名單 IP 訪問: {client_ip}")
                return Response(
                    content="Access Denied. Your IP has been blacklisted due to suspicious activity.",
                    status_code=403
                )
        except Exception as e:
            logger.debug(f"入侵檢測系統不可用: {e}")
            detector = None
        import time
        current_time = time.time()
        if client_ip not in self.clients:
            self.clients[client_ip] = []
        self.clients[client_ip] = [
            req_time for req_time in self.clients[client_ip]
            if current_time - req_time < self.period
        ]
        if len(self.clients[client_ip]) >= self.calls:
            logger.warning(f"⚠️ 速率限制: {client_ip} 超過限制 ({len(self.clients[client_ip])} requests)")
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
        self.clients[client_ip].append(current_time)
        if detector and len(self.clients[client_ip]) % 10 == 0:
            detector.record_event('api_request', client_ip)
        response = await call_next(request)
        return response
def validate_api_endpoint(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if os.getenv("ENVIRONMENT") == "production" and "ngrok" in parsed.netloc:
        raise ValueError(
            "Ngrok URLs are not allowed in production environment. "
            "Please use a proper domain name."
        )
    if os.getenv("ENVIRONMENT") == "production" and parsed.scheme != "https":
        logger.warning(f"Using non-HTTPS URL in production: {url}")
    return url