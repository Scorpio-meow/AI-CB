"""
增強的 API 訪問審計日誌系統
記錄所有管理員 API 調用和敏感操作
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import Request
import json
import os

# 配置審計日誌
AUDIT_LOG_DIR = "logs"
os.makedirs(AUDIT_LOG_DIR, exist_ok=True)

# 創建專門的審計日誌記錄器
audit_logger = logging.getLogger("api_audit")
audit_logger.setLevel(logging.INFO)

# 添加文件處理器
audit_file_handler = logging.FileHandler(
    os.path.join(AUDIT_LOG_DIR, "api_audit.log"),
    encoding='utf-8'
)
audit_file_handler.setLevel(logging.INFO)

# 設置審計日誌格式
audit_formatter = logging.Formatter(
    '%(asctime)s - [AUDIT] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
audit_file_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_file_handler)


class AuditLogger:
    """API 訪問審計日誌器"""
    
    @staticmethod
    def log_admin_api_access(
        request: Request,
        endpoint: str,
        user_id: Optional[int] = None,
        action: str = "UNKNOWN",
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        記錄管理員 API 訪問
        
        Args:
            request: FastAPI Request 對象
            endpoint: API 端點
            user_id: 用戶 ID
            action: 操作類型
            status: 操作狀態
            details: 額外詳情
        """
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
        
        audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    @staticmethod
    def log_authentication_event(
        request: Request,
        event_type: str,  # LOGIN, LOGOUT, REGISTER, TOKEN_REFRESH
        username: Optional[str] = None,
        status: str = "SUCCESS",
        reason: Optional[str] = None
    ):
        """
        記錄認證事件
        
        Args:
            request: FastAPI Request 對象
            event_type: 事件類型
            username: 用戶名
            status: 狀態
            reason: 失敗原因
        """
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
        
        audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    @staticmethod
    def log_data_modification(
        request: Request,
        resource_type: str,  # USER, DOCUMENT, CONVERSATION, etc.
        operation: str,  # CREATE, UPDATE, DELETE
        resource_id: Optional[int] = None,
        user_id: Optional[int] = None,
        changes: Optional[Dict[str, Any]] = None
    ):
        """
        記錄數據修改操作
        
        Args:
            request: FastAPI Request 對象
            resource_type: 資源類型
            resource_id: 資源 ID
            operation: 操作類型
            user_id: 操作用戶 ID
            changes: 變更內容
        """
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
        
        audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
    
    @staticmethod
    def log_security_event(
        request: Request,
        event_type: str,  # RATE_LIMIT_EXCEEDED, SUSPICIOUS_ACTIVITY, etc.
        severity: str = "WARNING",  # INFO, WARNING, CRITICAL
        details: Optional[Dict[str, Any]] = None
    ):
        """
        記錄安全事件
        
        Args:
            request: FastAPI Request 對象
            event_type: 事件類型
            severity: 嚴重程度
            details: 事件詳情
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "SECURITY_EVENT",
            "event": event_type,
            "severity": severity,
            "client_ip": request.client.host if request.client else "unknown",
            "details": details or {}
        }
        
        if severity == "CRITICAL":
            audit_logger.critical(json.dumps(log_entry, ensure_ascii=False))
        elif severity == "WARNING":
            audit_logger.warning(json.dumps(log_entry, ensure_ascii=False))
        else:
            audit_logger.info(json.dumps(log_entry, ensure_ascii=False))


# 導出單例
audit = AuditLogger()
