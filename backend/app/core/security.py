import os
import secrets
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
if not ADMIN_API_KEY or ADMIN_API_KEY == "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING":
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.warning("=" * 80)
    logger.warning("WARNING: ADMIN_API_KEY not set in environment!")
    logger.warning("Using temporary API key for development; set ADMIN_API_KEY in your environment.")
    logger.warning("Please set ADMIN_API_KEY in your .env file!")
    logger.warning("=" * 80)
async def verify_admin_api_key(x_api_key: Optional[str] = Header(None, description="Admin API Key")) -> bool:
    if not x_api_key:
        logger.warning("Admin API access attempt without API key")
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    if not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        logger.warning("Admin API access attempt with invalid API key")
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
                logger.error(f"拒絕黑名單 IP 訪問: {client_ip}")
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
            logger.warning(f"速率限制: {client_ip} 超過限制 ({len(self.clients[client_ip])} requests)")
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