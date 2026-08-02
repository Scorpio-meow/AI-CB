import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
import json
import os
from app.core.security_logging import sanitize_sensitive_data
AUDIT_LOG_DIR = "logs"
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)
audit_logger = logging.getLogger("api_audit")
audit_logger.setLevel(logging.INFO)
audit_file_handler = logging.FileHandler(
    os.path.join(AUDIT_LOG_DIR, "api_audit.log"),
    encoding='utf-8'
)
audit_file_handler.setLevel(logging.INFO)
audit_formatter = logging.Formatter(
    '%(asctime)s - [AUDIT] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
audit_file_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_file_handler)
class AuditLogger:
    
    @staticmethod
    def log_admin_api_access(
        request: Request,
        endpoint: str,
        user_id: Optional[int] = None,
        action: str = "UNKNOWN",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "ADMIN_API_ACCESS",
            "endpoint": endpoint,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "user_id": user_id,
            "action": action,
            "status": status,
            "details": details or {}
        }
        
        sanitized_entry = sanitize_sensitive_data(log_entry)
        audit_logger.info(json.dumps(sanitized_entry, ensure_ascii=False))
    
    @staticmethod
    def log_authentication_event(
        request: Request,
        event_type: str,
        username: Optional[str] = None,
        status: str = "SUCCESS",
        reason: Optional[str] = None
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "AUTHENTICATION",
            "event": event_type,
            "username": username,
            "status": status,
            "reason": reason,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown")
        }
        
        sanitized_entry = sanitize_sensitive_data(log_entry)
        audit_logger.info(json.dumps(sanitized_entry, ensure_ascii=False))
    
    @staticmethod
    def log_data_modification(
        request: Request,
        resource_type: str,
        operation: str,
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "DATA_MODIFICATION",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "operation": operation,
            "user_id": user_id,
            "changes": changes or {},
            "client_ip": request.client.host if request.client else "unknown"
        }
        
        sanitized_entry = sanitize_sensitive_data(log_entry)
        audit_logger.info(json.dumps(sanitized_entry, ensure_ascii=False))
    
    @staticmethod
    def log_security_event(
        request: Request,
        event_type: str,
        severity: str = "WARNING",
        details: Optional[Dict[str, Any]] = None
    ):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "SECURITY_EVENT",
            "event": event_type,
            "severity": severity,
            "client_ip": request.client.host if request.client else "unknown",
            "details": details or {}
        }
        
        sanitized_entry = sanitize_sensitive_data(log_entry)
        log_msg = json.dumps(sanitized_entry, ensure_ascii=False)
        if severity == "CRITICAL":
            audit_logger.critical(log_msg)
        elif severity == "WARNING":
            audit_logger.warning(log_msg)
        else:
            audit_logger.info(log_msg)
audit = AuditLogger()
