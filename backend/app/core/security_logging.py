"""
Security logging and monitoring utilities
"""
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
import os

# Configure security logger
security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

# Create security log file handler
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
security_log_file = os.path.join(log_dir, "security.log")

file_handler = logging.FileHandler(security_log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
security_logger.addHandler(file_handler)


class SecurityEvent:
    """安全事件類型"""
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
    """
    記錄安全事件
    
    Args:
        event_type: 事件類型（使用 SecurityEvent 類別的常量）
        request: FastAPI 請求對象（可選）
        user_id: 用戶 ID（可選）
        details: 額外的事件詳情（可選）
        severity: 嚴重程度 (INFO, WARNING, ERROR, CRITICAL)
    """
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
    
    # Log to security logger
    log_message = json.dumps(log_entry, ensure_ascii=False)
    
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
    """記錄檔案上傳事件"""
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
    """記錄管理員操作"""
    log_security_event(
        event_type=SecurityEvent.ADMIN_ACTION,
        request=request,
        details={
            "action": action,
            "target": target,
            **(details or {})
        },
        severity="WARNING"  # 管理員操作應該被特別關注
    )


def log_unauthorized_access(
    request: Request,
    reason: str,
    attempted_resource: Optional[str] = None
):
    """記錄未授權訪問嘗試"""
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
    """記錄可疑活動"""
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
    operation: str,  # "access", "modify", "delete"
    request: Request,
    user_id: int,
    resource_type: str,
    resource_id: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
):
    """記錄數據操作"""
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
