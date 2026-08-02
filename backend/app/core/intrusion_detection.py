
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import json
from pathlib import Path
logger = logging.getLogger(__name__)
class IntrusionDetector:
    
    def __init__(self, log_file: str = "logs/intrusion_detection.log"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        self.ip_events: Dict[str, List[Dict]] = defaultdict(list)
        
        self.blacklist: set = set()
        
        self.thresholds = {
            'failed_login_max': 5,
            'failed_login_window': 300,
            'api_requests_max': 1000,
            'api_requests_window': 3600,
            'file_uploads_max': 50,
            'file_uploads_window': 3600,
        }
    
    def record_event(
        self, 
        event_type: str, 
        ip_address: str, 
        user_id: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        event = {
            'timestamp': datetime.utcnow(),
            'type': event_type,
            'ip': ip_address,
            'user_id': user_id,
            'details': details or {}
        }
        
        self.ip_events[ip_address].append(event)
        
        self._cleanup_old_events(ip_address)
        
        self._check_for_threats(ip_address)
    
    def _cleanup_old_events(self, ip_address: str):
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.ip_events[ip_address] = [
            event for event in self.ip_events[ip_address]
            if event['timestamp'] > cutoff_time
        ]
    
    def _check_for_threats(self, ip_address: str):
        events = self.ip_events[ip_address]
        
        self._check_failed_logins(ip_address, events)
        
        self._check_api_requests(ip_address, events)
        
        self._check_file_uploads(ip_address, events)
    
    def _check_failed_logins(self, ip_address: str, events: List[Dict]):
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
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'ip_address': ip_address,
            'threat_type': threat_type,
            'message': message,
            'details': details
        }
        
        logger.warning(f"🚨 安全警報: {json.dumps(alert, ensure_ascii=False)}")
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(alert, ensure_ascii=False) + '\n')
    
    def is_blacklisted(self, ip_address: str) -> bool:
        return ip_address in self.blacklist
    
    def add_to_blacklist(self, ip_address: str, reason: str = ""):
        self.blacklist.add(ip_address)
        logger.warning(f"IP {ip_address} 已添加到黑名單。原因: {reason}")
    
    def remove_from_blacklist(self, ip_address: str):
        if ip_address in self.blacklist:
            self.blacklist.remove(ip_address)
            logger.info(f"IP {ip_address} 已從黑名單中移除")
    
    def get_suspicious_ips(self, limit: int = 10) -> List[Dict]:
        ip_scores = []
        
        for ip, events in self.ip_events.items():
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
        
        ip_scores.sort(key=lambda x: x['event_count'], reverse=True)
        
        return ip_scores[:limit]
_intrusion_detector_instance: Optional[IntrusionDetector] = None
def get_intrusion_detector() -> IntrusionDetector:
    global _intrusion_detector_instance
    
    if _intrusion_detector_instance is None:
        _intrusion_detector_instance = IntrusionDetector()
    
    return _intrusion_detector_instance
