
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
import threading
import json
from pathlib import Path
logger = logging.getLogger(__name__)
class SecurityMonitor:
    
    def __init__(self):
        self.events = deque(maxlen=10000)
        self.alert_thresholds = {
            'failed_login': 5,
            'invalid_token': 10,
            'file_upload_fail': 3,
            'api_rate_limit': 100,
        }
        self.tracking = defaultdict(lambda: defaultdict(int))
        self.lock = threading.Lock()
        
    def log_event(self, event_type: str, user_id: Optional[int] = None,
                  ip_address: Optional[str] = None, details: Optional[Dict] = None):
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {}
        }
        
        with self.lock:
            self.events.append(event)
            
            if ip_address:
                self.tracking[ip_address][event_type] += 1
            
            self._check_alerts(event)
        
        from app.core.security_logging import sanitize_sensitive_data
        sanitized_event = sanitize_sensitive_data(event)
        logger.info(f"SECURITY_EVENT: {json.dumps(sanitized_event, ensure_ascii=False)}")
    
    def _check_alerts(self, event: Dict[str, Any]):
        event_type = event['event_type']
        ip_address = event.get('ip_address')
        
        if not ip_address:
            return
        
        if event_type in self.alert_thresholds:
            threshold = self.alert_thresholds[event_type]
            count = self.tracking[ip_address][event_type]
            
            if count >= threshold:
                self._trigger_alert(event_type, ip_address, count)
    
    def _trigger_alert(self, event_type: str, ip_address: str, count: int):
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'alert_type': event_type,
            'ip_address': ip_address,
            'count': count,
            'threshold': self.alert_thresholds[event_type]
        }
        
        logger.warning(f"🚨 SECURITY_ALERT: {json.dumps(alert, ensure_ascii=False)}")
        
        self._send_alert_notification(alert)
    
    def _send_alert_notification(self, alert: Dict[str, Any]):
        pass
    
    def get_recent_events(self, event_type: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        with self.lock:
            events = list(self.events)
        
        if event_type:
            events = [e for e in events if e['event_type'] == event_type]
        
        return events[-limit:]
    
    def get_suspicious_ips(self, threshold: int = 10) -> List[Dict[str, Any]]:
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
        with self.lock:
            if ip_address:
                if ip_address in self.tracking:
                    del self.tracking[ip_address]
            else:
                self.tracking.clear()
    
    def export_events(self, output_file: str):
        with self.lock:
            events = list(self.events)
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
        
        logger.info(f"安全事件已導出到: {output_path}")
class AnomalyDetector:
    
    def __init__(self):
        self.baseline = {}
        self.window_size = timedelta(hours=1)
    
    def detect_anomaly(self, user_id: int, action: str) -> bool:
        key = f"{user_id}:{action}"
        current_time = datetime.utcnow()
        
        if key not in self.baseline:
            self.baseline[key] = {
                'count': 0,
                'last_reset': current_time
            }
        
        baseline = self.baseline[key]
        
        if current_time - baseline['last_reset'] > self.window_size:
            baseline['count'] = 0
            baseline['last_reset'] = current_time
        
        baseline['count'] += 1
        
        anomaly_thresholds = {
            'login': 10,
            'file_upload': 50,
            'api_call': 1000,
        }
        
        threshold = anomaly_thresholds.get(action, 100)
        return baseline['count'] > threshold
security_monitor = SecurityMonitor()
anomaly_detector = AnomalyDetector()
def log_security_event(event_type: str, **kwargs):
    security_monitor.log_event(event_type, **kwargs)
def check_anomaly(user_id: int, action: str) -> bool:
    return anomaly_detector.detect_anomaly(user_id, action)
