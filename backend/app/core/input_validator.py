"""
輸入驗證與清理模組
防止 XSS、SQL 注入、命令注入等攻擊
"""

import re
import html
import unicodedata
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """輸入驗證器"""
    
    # 危險字符模式
    DANGEROUS_PATTERNS = {
        'script_tags': r'<script[^>]*>.*?</script>',
        'javascript_protocol': r'javascript:',
        'on_event_handlers': r'\bon\w+\s*=',
        'sql_keywords': r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b',
        'command_injection': r'[;&|`$()]',
        'path_traversal': r'\.\.[/\\]',
    }
    
    # HTML 特殊字符
    HTML_ESCAPE_TABLE = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
    }
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 10000, 
                       allow_html: bool = False) -> str:
        """
        清理字符串輸入
        
        Args:
            input_str: 輸入字符串
            max_length: 最大長度
            allow_html: 是否允許 HTML（謹慎使用）
            
        Returns:
            清理後的字符串
        """
        if not input_str:
            return ""
        
        # 限制長度
        if len(input_str) > max_length:
            logger.warning(f"輸入長度超過限制: {len(input_str)} > {max_length}")
            input_str = input_str[:max_length]
        
        # Unicode 正規化
        input_str = unicodedata.normalize('NFKC', input_str)
        
        # 移除控制字符（保留換行符和製表符）
        input_str = ''.join(
            char for char in input_str 
            if char == '\n' or char == '\t' or not unicodedata.category(char).startswith('C')
        )
        
        if not allow_html:
            # 先移除危險模式（在編碼之前）
            for pattern_name, pattern in InputValidator.DANGEROUS_PATTERNS.items():
                if re.search(pattern, input_str, re.IGNORECASE):
                    logger.warning(f"檢測到危險模式: {pattern_name}")
                    input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)
            
            # HTML 實體編碼（移除危險模式後再編碼）
            input_str = InputValidator._escape_html(input_str)
        
        return input_str.strip()
    
    @staticmethod
    def _escape_html(text: str) -> str:
        """HTML 實體編碼"""
        return html.escape(text, quote=True)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        驗證電子郵件格式
        
        Args:
            email: 電子郵件地址
            
        Returns:
            是否有效
        """
        # RFC 5322 簡化版本
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or len(email) > 254:
            return False
        
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        """
        驗證用戶名
        
        Args:
            username: 用戶名
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        if not username:
            return False, "用戶名不能為空"
        
        if len(username) < 3:
            return False, "用戶名長度至少 3 個字符"
        
        if len(username) > 50:
            return False, "用戶名長度不能超過 50 個字符"
        
        # 只允許字母、數字、下劃線、連字符
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "用戶名只能包含字母、數字、下劃線和連字符"
        
        return True, ""
    
    @staticmethod
    def validate_filename(filename: str) -> tuple[bool, str]:
        """
        驗證文件名安全性
        
        Args:
            filename: 文件名
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        if not filename:
            return False, "文件名不能為空"
        
        if len(filename) > 255:
            return False, "文件名過長"
        
        # 危險字符
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            if char in filename:
                return False, f"文件名包含不允許的字符: {char}"
        
        # 檢查路徑遍歷
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return False, "檢測到路徑遍歷攻擊嘗試"
        
        # 檢查副檔名
        allowed_extensions = {'.txt', '.pdf', '.docx', '.jpg', '.png', '.gif'}
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in allowed_extensions:
            return False, f"不允許的文件類型: {ext}"
        
        return True, ""
    
    @staticmethod
    def sanitize_sql_input(input_str: str) -> str:
        """
        清理 SQL 輸入（額外的安全層，應配合參數化查詢使用）
        
        Args:
            input_str: 輸入字符串
            
        Returns:
            清理後的字符串
        """
        if not input_str:
            return ""
        
        # 移除所有 SQL 關鍵字
        sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'JOIN', 'WHERE', 'FROM',
            'TABLE', 'DATABASE', 'SCHEMA', 'INDEX', 'VIEW', 'PROCEDURE',
            'FUNCTION', 'TRIGGER', 'GRANT', 'REVOKE'
        ]
        
        result = input_str
        for keyword in sql_keywords:
            # 使用單詞邊界匹配，區分大小寫
            result = re.sub(r'\b' + keyword + r'\b', '', result, flags=re.IGNORECASE)
        
        # 移除 SQL 注入常見模式
        sql_patterns = [
            r"('\s*OR\s*'1'\s*=\s*'1)",
            r"('\s*OR\s*1\s*=\s*1)",
            r"(--)",
            r"(;)",
            r"(/\*.*?\*/)",
            r"(xp_)",
            r"(sp_)",
        ]
        
        for pattern in sql_patterns:
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
        
        return result.strip()
    
    @staticmethod
    def validate_json_input(json_str: str, max_size: int = 1024 * 1024) -> tuple[bool, str]:
        """
        驗證 JSON 輸入
        
        Args:
            json_str: JSON 字符串
            max_size: 最大大小（字節）
            
        Returns:
            (是否有效, 錯誤訊息)
        """
        if not json_str:
            return False, "JSON 輸入為空"
        
        if len(json_str.encode('utf-8')) > max_size:
            return False, f"JSON 大小超過限制: {max_size} 字節"
        
        try:
            import json
            json.loads(json_str)
            return True, ""
        except json.JSONDecodeError as e:
            return False, f"無效的 JSON 格式: {str(e)}"
    
    @staticmethod
    def sanitize_url(url: str) -> Optional[str]:
        """
        清理和驗證 URL
        
        Args:
            url: URL 字符串
            
        Returns:
            清理後的 URL 或 None
        """
        if not url:
            return None
        
        # 只允許 http 和 https 協議
        if not url.startswith(('http://', 'https://')):
            logger.warning(f"不允許的 URL 協議: {url}")
            return None
        
        # 檢查危險字符
        dangerous_chars = ['<', '>', '"', "'", '`', '{', '}', '|', '\\', '^', '[', ']']
        if any(char in url for char in dangerous_chars):
            logger.warning(f"URL 包含危險字符: {url}")
            return None
        
        return url
    
    @staticmethod
    def rate_limit_key(ip: str, endpoint: str) -> str:
        """
        生成速率限制鍵
        
        Args:
            ip: IP 地址
            endpoint: API 端點
            
        Returns:
            速率限制鍵
        """
        import hashlib
        combined = f"{ip}:{endpoint}"
        return hashlib.sha256(combined.encode()).hexdigest()


class InputSanitizer:
    """輸入清理器（快捷方式）"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本輸入"""
        return InputValidator.sanitize_string(text, allow_html=False)
    
    @staticmethod
    def clean_html(html_text: str) -> str:
        """清理 HTML 輸入（更嚴格）"""
        # 使用 bleach 庫會更好，但這裡提供基礎實現
        import html
        return html.escape(html_text, quote=True)
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """清理文件名"""
        # 移除危險字符
        cleaned = re.sub(r'[^\w\s.-]', '', filename)
        # 移除路徑分隔符
        cleaned = cleaned.replace('/', '').replace('\\', '')
        # 限制長度
        return cleaned[:255]


# 全局驗證器實例
validator = InputValidator()
sanitizer = InputSanitizer()
