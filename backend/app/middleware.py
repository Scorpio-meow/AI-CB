import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.security import (
    SecurityHeadersMiddleware, 
    RateLimitMiddleware
)
logger = logging.getLogger(__name__)
def setup_middlewares(app: FastAPI) -> None:
    app.add_middleware(SecurityHeadersMiddleware)
    logger.info("SecurityHeadersMiddleware loaded")
    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(
            RateLimitMiddleware, 
            calls=settings.RATE_LIMIT_PER_MINUTE, 
            period=60
        )
        logger.info(f"Rate limiting enabled: {settings.RATE_LIMIT_PER_MINUTE} requests per minute")
    allowed_origins = settings.allowed_origins_list
    cors_kwargs = {
        "allow_origins": allowed_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": ["*"],
    }
    
    app.add_middleware(
        CORSMiddleware,
        **cors_kwargs,
    )
    logger.info(f"CORS 白名單: {allowed_origins}")
    
    if settings.ENVIRONMENT == "production":
        logger.info("CORS 生產模式：嚴格白名單")
    else:
        logger.info("CORS 開發模式：精確白名單（無 regex）")
