
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
import os
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
security_log_file = os.path.join(log_dir, "security.log")
file_handler = logging.FileHandler(security_log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
security_logger.addHandler(file_handler)
import re
SENSITIVE_KEYS = {
    "password",
    "pass",
    "passwd",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "apikey",
    "authorization",
    "auth",
    "cred",
    "credentials",
    "private_key",
    "ssn",
    "card_number",
    "credit_card",
    "cookie",
}
SENSITIVE_JSON_RE = re.compile(
    r'(?i)("(?:password|passwd|pass|secret|token|access_token|refresh_token|api_key|apikey|authorization|auth|credentials|cred|private_key)"\s*:\s*)"[^"]*"',
)
def sanitize_sensitive_data(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            key_str = str(key)
            key_lower = key_str.lower()
            if any(s in key_lower for s in SENSITIVE_KEYS):
                sanitized[key_str] = "[REDACTED]"
            else:
                sanitized[key_str] = sanitize_sensitive_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_sensitive_data(item) for item in data)
    return data
class SecurityEvent:
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FILE_UPLOAD = "file_upload"
    FILE_UPLOAD_REJECTED = "file_upload_rejected"
    ADMIN_ACTION = "admin_action"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
def log_security_event(
    event_type: str,
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: str = "INFO"
):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "severity": severity,
        "user_id": user_id,
    }
    
    if request:
        log_entry.update({
            "client_ip": request.client.host if request.client else "unknown",
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("user-agent", "unknown"),
        })
    
    if details:
        log_entry["details"] = details
    
    sanitized_entry = sanitize_sensitive_data(log_entry)
    log_message = json.dumps(sanitized_entry, ensure_ascii=False)
    log_message = SENSITIVE_JSON_RE.sub(r'\1"[REDACTED]"', log_message)
    
    if severity == "CRITICAL":
        security_logger.critical(log_message)
    elif severity == "ERROR":
        security_logger.error(log_message)
    elif severity == "WARNING":
        security_logger.warning(log_message)
    else:
        security_logger.info(log_message)
def log_file_upload(
    request: Request,
    user_id: int,
    filename: str,
    file_size: int,
    status: str,
    details: Optional[str] = None
):
    log_security_event(
        event_type=SecurityEvent.FILE_UPLOAD if status == "success" else SecurityEvent.FILE_UPLOAD_REJECTED,
        request=request,
        user_id=user_id,
        details={
            "filename": filename,
            "file_size": file_size,
            "status": status,
            "message": details
        },
        severity="INFO" if status == "success" else "WARNING"
    )
def log_admin_action(
    request: Request,
    action: str,
    target: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    log_security_event(
        event_type=SecurityEvent.ADMIN_ACTION,
        request=request,
        details={
            "action": action,
            "target": target,
            **(details or {})
        },
        severity="WARNING"
    )
def log_unauthorized_access(
    request: Request,
    reason: str,
    attempted_resource: Optional[str] = None
):
    log_security_event(
        event_type=SecurityEvent.UNAUTHORIZED_ACCESS,
        request=request,
        details={
            "reason": reason,
            "attempted_resource": attempted_resource
        },
        severity="ERROR"
    )
def log_suspicious_activity(
    request: Request,
    activity: str,
    details: Optional[Dict[str, Any]] = None
):
    log_security_event(
        event_type=SecurityEvent.SUSPICIOUS_ACTIVITY,
        request=request,
        details={
            "activity": activity,
            **(details or {})
        },
        severity="CRITICAL"
    )
def log_data_operation(
    operation: str,
    request: Request,
    user_id: int,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
):
    event_types = {
        "access": SecurityEvent.DATA_ACCESS,
        "modify": SecurityEvent.DATA_MODIFICATION,
        "delete": SecurityEvent.DATA_DELETION
    }
    
    log_security_event(
        event_type=event_types.get(operation, SecurityEvent.DATA_ACCESS),
        request=request,
        user_id=user_id,
        details={
            "operation": operation,
            "resource_type": resource_type,
            "resource_id": resource_id,
            **(details or {})
        },
        severity="INFO" if operation == "access" else "WARNING"
    )
