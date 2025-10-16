"""
入侵檢測系統 (Intrusion Detection System)
監控和檢測可疑的安全事件
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class IntrusionDetector:
    """
    入侵檢測系統
    
    監控以下可疑行為：
    1. 異常高頻率的 API 請求
    2. 多次失敗的認證嘗試
    3. 可疑的文件上傳行為
    4. 異常的 Admin API 訪問
    """
    
    def __init__(self, log_file: str = "logs/intrusion_detection.log"):
        """
        初始化入侵檢測系統
        
        Args:
            log_file: 日誌文件路徑
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 記錄每個 IP 的事件
        self.ip_events: Dict[str, List[Dict]] = defaultdict(list)
        
        # 黑名單
        self.blacklist: set = set()
        
        # 配置閾值
        self.thresholds = {
            'failed_login_max': 5,          # 最多失敗登入次數
            'failed_login_window': 300,     # 時間窗口（秒）
            'api_requests_max': 1000,       # 最大 API 請求數
            'api_requests_window': 3600,    # 時間窗口（秒）
            'file_uploads_max': 50,         # 最大文件上傳數
            'file_uploads_window': 3600,    # 時間窗口（秒）
        }
    
    def record_event(
        self, 
        event_type: str, 
        ip_address: str, 
        user_id: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        """
        記錄安全事件
        
        Args:
            event_type: 事件類型（failed_login, api_request, file_upload 等）
            ip_address: IP 地址
            user_id: 用戶 ID（可選）
            details: 額外詳情
        """
        event = {
            'timestamp': datetime.utcnow(),
            'type': event_type,
            'ip': ip_address,
            'user_id': user_id,
            'details': details or {}
        }
        
        self.ip_events[ip_address].append(event)
        
        # 清理舊事件（保留 24 小時內的事件）
        self._cleanup_old_events(ip_address)
        
        # 檢查是否觸發警報
        self._check_for_threats(ip_address)
    
    def _cleanup_old_events(self, ip_address: str):
        """清理 24 小時前的事件"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.ip_events[ip_address] = [
            event for event in self.ip_events[ip_address]
            if event['timestamp'] > cutoff_time
        ]
    
    def _check_for_threats(self, ip_address: str):
        """檢查是否有可疑行為"""
        events = self.ip_events[ip_address]
        
        # 檢查失敗登入
        self._check_failed_logins(ip_address, events)
        
        # 檢查 API 請求頻率
        self._check_api_requests(ip_address, events)
        
        # 檢查文件上傳頻率
        self._check_file_uploads(ip_address, events)
    
    def _check_failed_logins(self, ip_address: str, events: List[Dict]):
        """檢查失敗的登入嘗試"""
        cutoff_time = datetime.utcnow() - timedelta(
            seconds=self.thresholds['failed_login_window']
        )
        
        failed_logins = [
            e for e in events 
            if e['type'] == 'failed_login' and e['timestamp'] > cutoff_time
        ]
        
        if len(failed_logins) >= self.thresholds['failed_login_max']:
            self._trigger_alert(
                ip_address,
                'BRUTE_FORCE_ATTACK',
                f"檢測到 {len(failed_logins)} 次失敗的登入嘗試",
                {'failed_attempts': len(failed_logins)}
            )
            self.blacklist.add(ip_address)
    
    def _check_api_requests(self, ip_address: str, events: List[Dict]):
        """檢查 API 請求頻率"""
        cutoff_time = datetime.utcnow() - timedelta(
            seconds=self.thresholds['api_requests_window']
        )
        
        api_requests = [
            e for e in events 
            if e['type'] == 'api_request' and e['timestamp'] > cutoff_time
        ]
        
        if len(api_requests) >= self.thresholds['api_requests_max']:
            self._trigger_alert(
                ip_address,
                'DDOS_ATTACK',
                f"檢測到異常高頻率的 API 請求: {len(api_requests)} 次",
                {'request_count': len(api_requests)}
            )
    
    def _check_file_uploads(self, ip_address: str, events: List[Dict]):
        """檢查文件上傳頻率"""
        cutoff_time = datetime.utcnow() - timedelta(
            seconds=self.thresholds['file_uploads_window']
        )
        
        file_uploads = [
            e for e in events 
            if e['type'] == 'file_upload' and e['timestamp'] > cutoff_time
        ]
        
        if len(file_uploads) >= self.thresholds['file_uploads_max']:
            self._trigger_alert(
                ip_address,
                'SUSPICIOUS_FILE_UPLOAD',
                f"檢測到異常高頻率的文件上傳: {len(file_uploads)} 次",
                {'upload_count': len(file_uploads)}
            )
    
    def _trigger_alert(
        self, 
        ip_address: str, 
        threat_type: str, 
        message: str,
        details: Dict
    ):
        """
        觸發安全警報
        
        Args:
            ip_address: 可疑 IP 地址
            threat_type: 威脅類型
            message: 警報消息
            details: 詳細信息
        """
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': ip_address,
            'threat_type': threat_type,
            'message': message,
            'details': details
        }
        
        # 記錄到日誌
        logger.warning(f"🚨 安全警報: {json.dumps(alert, ensure_ascii=False)}")
        
        # 保存到文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')
    
    def is_blacklisted(self, ip_address: str) -> bool:
        """檢查 IP 是否在黑名單中"""
        return ip_address in self.blacklist
    
    def add_to_blacklist(self, ip_address: str, reason: str = ""):
        """手動添加到黑名單"""
        self.blacklist.add(ip_address)
        logger.warning(f"IP {ip_address} 已添加到黑名單。原因: {reason}")
    
    def remove_from_blacklist(self, ip_address: str):
        """從黑名單中移除"""
        if ip_address in self.blacklist:
            self.blacklist.remove(ip_address)
            logger.info(f"IP {ip_address} 已從黑名單中移除")
    
    def get_suspicious_ips(self, limit: int = 10) -> List[Dict]:
        """
        獲取最可疑的 IP 列表
        
        Args:
            limit: 返回數量
            
        Returns:
            可疑 IP 列表，按事件數量排序
        """
        ip_scores = []
        
        for ip, events in self.ip_events.items():
            # 計算最近1小時的事件數
            recent_events = [
                e for e in events 
                if e['timestamp'] > datetime.utcnow() - timedelta(hours=1)
            ]
            
            if recent_events:
                ip_scores.append({
                    'ip': ip,
                    'event_count': len(recent_events),
                    'failed_logins': len([e for e in recent_events if e['type'] == 'failed_login']),
                    'is_blacklisted': ip in self.blacklist
                })
        
        # 按事件數量排序
        ip_scores.sort(key=lambda x: x['event_count'], reverse=True)
        
        return ip_scores[:limit]


# 全局實例
_intrusion_detector_instance: Optional[IntrusionDetector] = None


def get_intrusion_detector() -> IntrusionDetector:
    """獲取入侵檢測器的全局實例（單例模式）"""
    global _intrusion_detector_instance
    
    if _intrusion_detector_instance is None:
        _intrusion_detector_instance = IntrusionDetector()
    
    return _intrusion_detector_instance
