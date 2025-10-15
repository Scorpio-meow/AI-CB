"""
安全功能測試套件
"""

import pytest
from app.core.input_validator import InputValidator, InputSanitizer
from app.core.security_monitor import SecurityMonitor, AnomalyDetector

class TestInputValidator:
    """輸入驗證測試"""
    
    def test_sanitize_string_xss(self):
        """測試 XSS 防護"""
        malicious = '<script>alert("XSS")</script>'
        result = InputValidator.sanitize_string(malicious)
        assert '<script>' not in result
        assert 'alert' not in result
    
    def test_sanitize_string_sql_injection(self):
        """測試 SQL 注入防護"""
        malicious = "'; DROP TABLE users; --"
        result = InputValidator.sanitize_sql_input(malicious)
        assert 'DROP' not in result.upper()
        assert '--' not in result
    
    def test_validate_email_valid(self):
        """測試有效郵箱"""
        valid_emails = [
            'user@example.com',
            'test.user@company.co.uk',
            'user+tag@domain.org'
        ]
        for email in valid_emails:
            assert InputValidator.validate_email(email) is True
    
    def test_validate_email_invalid(self):
        """測試無效郵箱"""
        invalid_emails = [
            'invalid',
            '@example.com',
            'user@',
            'user space@example.com',
            'user<script>@example.com'
        ]
        for email in invalid_emails:
            assert InputValidator.validate_email(email) is False
    
    def test_validate_username_valid(self):
        """測試有效用戶名"""
        valid, msg = InputValidator.validate_username('valid_user123')
        assert valid is True
        assert msg == ""
    
    def test_validate_username_invalid(self):
        """測試無效用戶名"""
        # 太短
        valid, msg = InputValidator.validate_username('ab')
        assert valid is False
        
        # 包含特殊字符
        valid, msg = InputValidator.validate_username('user@name')
        assert valid is False
        
        # 太長
        valid, msg = InputValidator.validate_username('a' * 51)
        assert valid is False
    
    def test_validate_filename_path_traversal(self):
        """測試路徑遍歷攻擊"""
        dangerous_names = [
            '../../../etc/passwd',
            '..\\windows\\system32',
            'file/../../../secret.txt'
        ]
        for name in dangerous_names:
            valid, msg = InputValidator.validate_filename(name)
            assert valid is False
            assert '遍歷' in msg or '字符' in msg
    
    def test_validate_filename_dangerous_chars(self):
        """測試危險字符"""
        dangerous = 'file<script>.txt'
        valid, msg = InputValidator.validate_filename(dangerous)
        assert valid is False
    
    def test_sanitize_url_valid(self):
        """測試有效 URL"""
        valid_urls = [
            'https://example.com',
            'http://api.service.com/endpoint'
        ]
        for url in valid_urls:
            result = InputValidator.sanitize_url(url)
            assert result is not None
    
    def test_sanitize_url_invalid_protocol(self):
        """測試無效協議"""
        invalid_urls = [
            'javascript:alert(1)',
            'file:///etc/passwd',
            'ftp://server.com'
        ]
        for url in invalid_urls:
            result = InputValidator.sanitize_url(url)
            assert result is None


class TestSecurityMonitor:
    """安全監控測試"""
    
    def test_log_event(self):
        """測試事件記錄"""
        monitor = SecurityMonitor()
        monitor.log_event('test_event', user_id=1, ip_address='127.0.0.1')
        
        events = monitor.get_recent_events(event_type='test_event')
        assert len(events) >= 1
        assert events[-1]['event_type'] == 'test_event'
    
    def test_alert_threshold(self):
        """測試告警閾值"""
        monitor = SecurityMonitor()
        ip = '192.168.1.100'
        
        # 模擬多次失敗登入
        for i in range(6):
            monitor.log_event('failed_login', ip_address=ip)
        
        # 檢查是否觸發告警（通過日誌）
        assert monitor.tracking[ip]['failed_login'] >= 5
    
    def test_get_suspicious_ips(self):
        """測試可疑 IP 檢測"""
        monitor = SecurityMonitor()
        ip = '10.0.0.1'
        
        for i in range(15):
            monitor.log_event('api_call', ip_address=ip)
        
        suspicious = monitor.get_suspicious_ips(threshold=10)
        assert len(suspicious) > 0
        assert suspicious[0]['ip_address'] == ip


class TestAnomalyDetector:
    """異常檢測測試"""
    
    def test_normal_behavior(self):
        """測試正常行為"""
        detector = AnomalyDetector()
        
        # 正常登入次數
        for i in range(5):
            is_anomaly = detector.detect_anomaly(user_id=1, action='login')
        
        assert is_anomaly is False
    
    def test_anomaly_detection(self):
        """測試異常行為檢測"""
        detector = AnomalyDetector()
        
        # 異常登入次數
        is_anomaly = False
        for i in range(12):
            is_anomaly = detector.detect_anomaly(user_id=1, action='login')
        
        assert is_anomaly is True


class TestPasswordStrength:
    """密碼強度測試"""
    
    def test_weak_passwords(self):
        """測試弱密碼"""
        from app.core.jwt_auth import validate_password_strength
        
        weak_passwords = [
            'password',
            '12345678',
            'abcdefgh',
            'ABCDEFGH',
            'short'
        ]
        
        for pwd in weak_passwords:
            valid, msg = validate_password_strength(pwd)
            assert valid is False
    
    def test_strong_passwords(self):
        """測試強密碼"""
        from app.core.jwt_auth import validate_password_strength
        
        strong_passwords = [
            'SecurePass123',
            'MyP@ssw0rd!',
            'Tr0ng_P4ss'
        ]
        
        for pwd in strong_passwords:
            valid, msg = validate_password_strength(pwd)
            assert valid is True
            assert msg == ""


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
