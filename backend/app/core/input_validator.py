
import re
import html
import unicodedata
from typing import Optional, List
import logging
logger = logging.getLogger(__name__)
class InputValidator:
    
    DANGEROUS_PATTERNS = {
        'script_tags': r'<script[^>]*>.*?</script>',
        'javascript_protocol': r'javascript:',
        'on_event_handlers': r'\bon\w+\s*=',
        'sql_keywords': r'\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|EXECUTE)\b',
        'command_injection': r'[;&|`$()]',
        'path_traversal': r'\.\.[/\\]',
    }
    
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
        if not input_str:
            return ""
        
        if len(input_str) > max_length:
            logger.warning(f"輸入長度超過限制: {len(input_str)} > {max_length}")
            input_str = input_str[:max_length]
        
        input_str = unicodedata.normalize('NFKC', input_str)
        
        input_str = ''.join(
            char for char in input_str 
            if char == '\n' or char == '\t' or not unicodedata.category(char).startswith('C')
        )
        
        if not allow_html:
            for pattern_name, pattern in InputValidator.DANGEROUS_PATTERNS.items():
                if re.search(pattern, input_str, re.IGNORECASE):
                    logger.warning(f"檢測到危險模式: {pattern_name}")
                    input_str = re.sub(pattern, '', input_str, flags=re.IGNORECASE)
            
            input_str = InputValidator._escape_html(input_str)
        
        return input_str.strip()
    
    @staticmethod
    def _escape_html(text: str) -> str:
        return html.escape(text, quote=True)
    
    @staticmethod
    def validate_email(email: str) -> bool:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not email or len(email) > 254:
            return False
        
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_username(username: str) -> tuple[bool, str]:
        if not username:
            return False, "用戶名不能為空"
        
        if len(username) < 3:
            return False, "用戶名長度至少 3 個字符"
        
        if len(username) > 50:
            return False, "用戶名長度不能超過 50 個字符"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "用戶名只能包含字母、數字、下劃線和連字符"
        
        return True, ""
    
    @staticmethod
    def validate_filename(filename: str) -> tuple[bool, str]:
        if not filename:
            return False, "文件名不能為空"
        
        if len(filename) > 255:
            return False, "文件名過長"
        
        dangerous_chars = ['/', '\\', '..', '<', '>', ':', '"', '|', '?', '*', '\0']
        for char in dangerous_chars:
            if char in filename:
                return False, f"文件名包含不允許的字符: {char}"
        
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            return False, "檢測到路徑遍歷攻擊嘗試"
        
        allowed_extensions = {
            '.txt', '.md', '.markdown', '.pdf', '.docx', '.doc', '.pptx',
            '.xlsx', '.xls', '.csv', '.json', '.yaml', '.yml', '.xml',
            '.html', '.htm', '.log', '.py', '.js', '.ts', '.tsx', '.jsx',
            '.java', '.cpp', '.c', '.sql', '.sh', '.ini', '.env',
            '.jpg', '.png', '.gif'
        }
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in allowed_extensions:
            return False, f"不允許的文件類型: {ext}"

        return True, ""
    
    @staticmethod
    def sanitize_sql_input(input_str: str) -> str:
        if not input_str:
            return ""
        
        sql_keywords = [
            'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'EXEC', 'EXECUTE', 'UNION', 'JOIN', 'WHERE', 'FROM',
            'TABLE', 'DATABASE', 'SCHEMA', 'INDEX', 'VIEW', 'PROCEDURE',
            'FUNCTION', 'TRIGGER', 'GRANT', 'REVOKE'
        ]
        
        result = input_str
        for keyword in sql_keywords:
            result = re.sub(r'\b' + keyword + r'\b', '', result, flags=re.IGNORECASE)
        
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
        if not url:
            return None
        
        if not url.startswith(('http://', 'https://')):
            logger.warning(f"不允許的 URL 協議: {url}")
            return None
        
        dangerous_chars = ['<', '>', '"', "'", '`', '{', '}', '|', '\\', '^', '[', ']']
        if any(char in url for char in dangerous_chars):
            logger.warning(f"URL 包含危險字符: {url}")
            return None
        
        return url
    
    @staticmethod
    def rate_limit_key(ip: str, endpoint: str) -> str:
        import hashlib
        combined = f"{ip}:{endpoint}"
        return hashlib.sha256(combined.encode()).hexdigest()
class InputSanitizer:
    
    @staticmethod
    def clean_text(text: str) -> str:
        return InputValidator.sanitize_string(text, allow_html=False)
    
    @staticmethod
    def clean_html(html_text: str) -> str:
        import html
        return html.escape(html_text, quote=True)
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        cleaned = re.sub(r'[^\w\s.-]', '', filename)
        cleaned = cleaned.replace('/', '').replace('\\', '')
        return cleaned[:255]
validator = InputValidator()
sanitizer = InputSanitizer()
