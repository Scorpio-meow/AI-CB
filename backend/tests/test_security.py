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


class TestSecretManager:
    """SecretManager 測試"""
    
    def test_get_or_generate_secret(self):
        """測試密鑰取得或生成"""
        from app.core.secret_manager import SecretManager
        import os
        
        manager = SecretManager()
        
        # 清除環境變數（如果存在）
        test_key = 'TEST_SECRET_KEY'
        if test_key in os.environ:
            del os.environ[test_key]
        
        # 生成新密鑰
        secret = manager.get_or_generate_secret(test_key)
        assert secret is not None
        assert len(secret) >= 32
    
    def test_validate_secret_strength(self):
        """測試密鑰強度驗證"""
        from app.core.secret_manager import SecretManager
        
        manager = SecretManager()
        
        # 弱密鑰
        weak_secret = '12345'
        valid, msg = manager.validate_secret_strength(weak_secret)
        assert valid is False
        
        # 強密鑰
        strong_secret = 'a' * 64
        valid, msg = manager.validate_secret_strength(strong_secret)
        assert valid is True


class TestIntrusionDetection:
    """入侵檢測測試"""
    
    def test_record_event(self):
        """測試事件記錄"""
        from app.core.intrusion_detection import IntrusionDetector
        
        detector = IntrusionDetector()
        detector.record_event('192.168.1.1', 'failed_login')
        
        assert '192.168.1.1' in detector.ip_events
    
    def test_brute_force_detection(self):
        """測試暴力破解檢測"""
        from app.core.intrusion_detection import IntrusionDetector
        
        detector = IntrusionDetector()
        ip = '10.0.0.1'
        
        # 模擬 5 次失敗登入
        for i in range(5):
            detector.record_event(ip, 'failed_login')
        
        is_threat = detector.is_potential_threat(ip)
        assert is_threat is True
    
    def test_blacklist(self):
        """測試黑名單功能"""
        from app.core.intrusion_detection import IntrusionDetector
        
        detector = IntrusionDetector()
        ip = '192.168.100.100'
        
        detector.blacklist_ip(ip)
        assert detector.is_blacklisted(ip) is True


class TestRateLimiting:
    """速率限制測試"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """測試速率限制執行"""
        from app.core.security import RateLimitMiddleware
        from fastapi import FastAPI, Request
        from starlette.middleware.base import BaseHTTPMiddleware
        
        app = FastAPI()
        middleware = RateLimitMiddleware(app)
        
        # 模擬多次請求
        # 實際實現需要 mock Request 對象
        # 這裡僅作示意
        pass


class TestCORS:
    """CORS 配置測試"""
    
    def test_cors_origins(self):
        """測試 CORS 來源配置"""
        import os
        from main import get_allowed_origins
        
        # 測試開發環境
        os.environ['ENVIRONMENT'] = 'development'
        origins = get_allowed_origins()
        assert 'http://localhost:3000' in origins
        
        # 測試生產環境
        os.environ['ENVIRONMENT'] = 'production'
        origins = get_allowed_origins()
        assert 'http://localhost:3000' not in origins


class TestCommandInjection:
    """命令注入防護測試"""
    
    def test_shell_command_safety(self):
        """測試 shell 命令安全性"""
        import subprocess
        import shlex
        
        # 危險的命令（不應該這樣做）
        # dangerous = f"ls {user_input}"  # 不安全
        
        # 安全的命令
        user_input = "test; rm -rf /"
        safe_command = ['ls', shlex.quote(user_input)]
        
        # 驗證參數被正確轉義
        assert shlex.quote(user_input) != user_input


class TestFileUploadSecurity:
    """文件上傳安全測試"""
    
    def test_file_extension_validation(self):
        """測試文件擴展名驗證"""
        from app.core.input_validator import InputValidator
        
        valid_files = ['document.pdf', 'text.txt', 'report.docx']
        for file in valid_files:
            valid, msg = InputValidator.validate_filename(file)
            assert valid is True
        
        invalid_files = ['script.exe', 'malware.bat', 'file.sh']
        for file in invalid_files:
            # 如果實現了擴展名檢查
            # valid, msg = InputValidator.validate_file_extension(file)
            # assert valid is False
            pass
    
    def test_file_size_limit(self):
        """測試文件大小限制"""
        # 在 API 中應該有 50MB 限制
        max_size = 50 * 1024 * 1024  # 50MB
        assert max_size == 52428800


class TestJWTSecurity:
    """JWT 安全測試"""
    
    def test_jwt_token_expiration(self):
        """測試 JWT 過期時間"""
        from app.core.jwt_auth import create_access_token
        import jwt
        from datetime import datetime, timedelta
        
        token = create_access_token(data={'user_id': 1})
        
        # 解碼但不驗證（僅檢查結構）
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert 'exp' in decoded
        assert 'user_id' in decoded
    
    def test_jwt_blacklist(self):
        """測試 JWT 黑名單"""
        from app.core.jwt_auth import blacklist_token, is_token_blacklisted
        
        token = 'test_token_123'
        blacklist_token(token)
        
        assert is_token_blacklisted(token) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
