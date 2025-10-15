"""
安全監控模組
實時監控安全事件、異常行為和潛在攻擊
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """安全監控器"""
    
    def __init__(self):
        self.events = deque(maxlen=10000)  # 保留最近 10000 個事件
        self.alert_thresholds = {
            'failed_login': 5,  # 5 次失敗登入
            'invalid_token': 10,  # 10 次無效 token
            'file_upload_fail': 3,  # 3 次文件上傳失敗
            'api_rate_limit': 100,  # 每分鐘 100 次請求
        }
        self.tracking = defaultdict(lambda: defaultdict(int))
        self.lock = threading.Lock()
        
    def log_event(self, event_type: str, user_id: Optional[int] = None,
                  ip_address: Optional[str] = None, details: Optional[Dict] = None):
        """
        記錄安全事件
        
        Args:
            event_type: 事件類型
            user_id: 用戶 ID
            ip_address: IP 地址
            details: 事件詳情
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {}
        }
        
        with self.lock:
            self.events.append(event)
            
            # 更新追蹤計數
            if ip_address:
                self.tracking[ip_address][event_type] += 1
            
            # 檢查是否需要告警
            self._check_alerts(event)
        
        # 記錄到日誌
        logger.info(f"SECURITY_EVENT: {json.dumps(event, ensure_ascii=False)}")
    
    def _check_alerts(self, event: Dict[str, Any]):
        """檢查是否觸發告警"""
        event_type = event['event_type']
        ip_address = event.get('ip_address')
        
        if not ip_address:
            return
        
        # 檢查閾值
        if event_type in self.alert_thresholds:
            threshold = self.alert_thresholds[event_type]
            count = self.tracking[ip_address][event_type]
            
            if count >= threshold:
                self._trigger_alert(event_type, ip_address, count)
    
    def _trigger_alert(self, event_type: str, ip_address: str, count: int):
        """觸發安全告警"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': event_type,
            'ip_address': ip_address,
            'count': count,
            'threshold': self.alert_thresholds[event_type]
        }
        
        logger.warning(f"🚨 SECURITY_ALERT: {json.dumps(alert, ensure_ascii=False)}")
        
        # 這裡可以添加通知機制（郵件、Slack 等）
        self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Dict[str, Any]):
        """發送告警通知"""
        # TODO: 實現郵件或其他通知方式
        pass
    
    def get_recent_events(self, event_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """
        獲取最近的安全事件
        
        Args:
            event_type: 事件類型過濾
            limit: 返回數量限制
            
        Returns:
            事件列表
        """
        with self.lock:
            events = list(self.events)
        
        if event_type:
            events = [e for e in events if e['event_type'] == event_type]
        
        return events[-limit:]
    
    def get_suspicious_ips(self, threshold: int = 10) -> List[Dict[str, Any]]:
        """
        獲取可疑 IP 列表
        
        Args:
            threshold: 可疑行為閾值
            
        Returns:
            可疑 IP 列表
        """
        suspicious = []
        
        with self.lock:
            for ip, events in self.tracking.items():
                total_events = sum(events.values())
                if total_events >= threshold:
                    suspicious.append({
                        'ip_address': ip,
                        'total_events': total_events,
                        'event_breakdown': dict(events)
                    })
        
        return sorted(suspicious, key=lambda x: x['total_events'], reverse=True)
    
    def reset_tracking(self, ip_address: Optional[str] = None):
        """
        重置追蹤計數
        
        Args:
            ip_address: 指定 IP（None 則重置全部）
        """
        with self.lock:
            if ip_address:
                if ip_address in self.tracking:
                    del self.tracking[ip_address]
            else:
                self.tracking.clear()
    
    def export_events(self, output_file: str):
        """
        導出事件到文件
        
        Args:
            output_file: 輸出文件路徑
        """
        with self.lock:
            events = list(self.events)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        
        logger.info(f"安全事件已導出到: {output_path}")


class AnomalyDetector:
    """異常行為檢測器"""
    
    def __init__(self):
        self.baseline = {}
        self.window_size = timedelta(hours=1)
    
    def detect_anomaly(self, user_id: int, action: str) -> bool:
        """
        檢測異常行為
        
        Args:
            user_id: 用戶 ID
            action: 行為類型
            
        Returns:
            是否為異常行為
        """
        # 簡單的異常檢測（可以用更複雜的 ML 模型）
        key = f"{user_id}:{action}"
        current_time = datetime.utcnow()
        
        if key not in self.baseline:
            self.baseline[key] = {
                'count': 0,
                'last_reset': current_time
            }
        
        baseline = self.baseline[key]
        
        # 時間窗口重置
        if current_time - baseline['last_reset'] > self.window_size:
            baseline['count'] = 0
            baseline['last_reset'] = current_time
        
        baseline['count'] += 1
        
        # 異常檢測規則
        anomaly_thresholds = {
            'login': 10,  # 1小時內登入超過 10 次
            'file_upload': 50,  # 1小時內上傳超過 50 個文件
            'api_call': 1000,  # 1小時內 API 調用超過 1000 次
        }
        
        threshold = anomaly_thresholds.get(action, 100)
        return baseline['count'] > threshold


# 全局監控器實例
security_monitor = SecurityMonitor()
anomaly_detector = AnomalyDetector()


def log_security_event(event_type: str, **kwargs):
    """便捷的安全事件記錄函數"""
    security_monitor.log_event(event_type, **kwargs)


def check_anomaly(user_id: int, action: str) -> bool:
    """便捷的異常檢測函數"""
    return anomaly_detector.detect_anomaly(user_id, action)
