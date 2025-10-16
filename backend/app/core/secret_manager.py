"""
安全的密鑰管理系統
提供密鑰的安全生成、存儲和檢索
"""

import os
import secrets
import logging
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import json

logger = logging.getLogger(__name__)


class SecretManager:
    """
    安全的密鑰管理器
    
    優先級：
    1. 環境變數（最高優先級）
    2. 加密的密鑰文件
    3. 自動生成新密鑰
    """
    
    def __init__(self, secrets_file: str = "secrets.enc"):
        """
        初始化密鑰管理器
        
        Args:
            secrets_file: 加密的密鑰文件路徑
        """
        self.secrets_file = Path(secrets_file)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """
        獲取或創建加密密鑰（用於加密密鑰文件本身）
        這個密鑰從系統環境變數中獲取
        """
        key_env = os.getenv("SECRETS_ENCRYPTION_KEY")
        
        if key_env:
            # 確保密鑰格式正確
            try:
                return key_env.encode('utf-8')
            except Exception:
                logger.warning("環境變數中的加密密鑰格式不正確")
        
        # 生成新的加密密鑰
        new_key = Fernet.generate_key()
        logger.warning(
            f"⚠️  未找到 SECRETS_ENCRYPTION_KEY 環境變數\n"
            f"⚠️  已生成新的加密密鑰: {new_key.decode('utf-8')}\n"
            f"⚠️  請將此密鑰添加到環境變數中以保證數據持久性"
        )
        return new_key
    
    def get_or_generate_secret(
        self, 
        key_name: str, 
        length: int = 32,
        force_regenerate: bool = False
    ) -> str:
        """
        獲取或生成密鑰
        
        Args:
            key_name: 密鑰名稱（如 'ADMIN_API_KEY'）
            length: 密鑰長度（字節數）
            force_regenerate: 是否強制重新生成
            
        Returns:
            密鑰字符串
        """
        # 1. 首先檢查環境變數
        if not force_regenerate:
            secret = os.getenv(key_name)
            if secret:
                logger.info(f"從環境變數載入密鑰: {key_name}")
                return secret
        
        # 2. 檢查加密的密鑰文件
        if not force_regenerate and self.secrets_file.exists():
            secret = self._load_from_encrypted_file(key_name)
            if secret:
                logger.info(f"從加密文件載入密鑰: {key_name}")
                return secret
        
        # 3. 生成新密鑰並保存
        new_secret = secrets.token_urlsafe(length)
        self._save_to_encrypted_file(key_name, new_secret)
        
        logger.warning(
            f"🔑 生成新的 {key_name}\n"
            f"   前10字符: {new_secret[:10]}...\n"
            f"   建議將此密鑰添加到 .env 文件中"
        )
        
        return new_secret
    
    def _load_from_encrypted_file(self, key_name: str) -> Optional[str]:
        """從加密文件中載入密鑰"""
        try:
            with open(self.secrets_file, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.cipher.decrypt(encrypted_data)
            secrets_dict = json.loads(decrypted_data.decode('utf-8'))
            
            return secrets_dict.get(key_name)
        
        except Exception as e:
            logger.debug(f"無法從加密文件載入 {key_name}: {e}")
            return None
    
    def _save_to_encrypted_file(self, key_name: str, value: str):
        """將密鑰保存到加密文件"""
        try:
            # 載入現有的密鑰（如果有）
            secrets_dict = {}
            if self.secrets_file.exists():
                try:
                    with open(self.secrets_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    secrets_dict = json.loads(decrypted_data.decode('utf-8'))
                except Exception:
                    pass  # 如果讀取失敗，使用空字典
            
            # 添加新密鑰
            secrets_dict[key_name] = value
            
            # 加密並保存
            data_to_encrypt = json.dumps(secrets_dict).encode('utf-8')
            encrypted_data = self.cipher.encrypt(data_to_encrypt)
            
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            # 設置文件權限（僅擁有者可讀寫）
            if os.name != 'nt':  # Unix/Linux 系統
                os.chmod(self.secrets_file, 0o600)
            
            logger.info(f"密鑰 {key_name} 已加密保存")
        
        except Exception as e:
            logger.error(f"保存密鑰失敗: {e}")
    
    def rotate_secret(self, key_name: str, length: int = 32) -> str:
        """
        輪換密鑰（生成新密鑰並保存舊密鑰供過渡使用）
        
        Args:
            key_name: 密鑰名稱
            length: 新密鑰長度
            
        Returns:
            新密鑰
        """
        # 保存舊密鑰到歷史記錄
        old_secret = self.get_or_generate_secret(key_name, length)
        self._save_to_encrypted_file(f"{key_name}_OLD", old_secret)
        
        # 生成新密鑰
        new_secret = self.get_or_generate_secret(key_name, length, force_regenerate=True)
        
        logger.info(f"密鑰 {key_name} 已輪換，舊密鑰保存為 {key_name}_OLD")
        
        return new_secret
    
    def validate_secret_strength(self, secret: str) -> tuple[bool, str]:
        """
        驗證密鑰強度
        
        Args:
            secret: 待驗證的密鑰
            
        Returns:
            (是否有效, 錯誤消息)
        """
        if len(secret) < 32:
            return False, "密鑰長度至少需要 32 個字符"
        
        # 檢查是否包含多種字符類型
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        
        if not (has_upper and has_lower and has_digit):
            return False, "密鑰應包含大寫字母、小寫字母和數字"
        
        # 檢查是否有明顯的模式
        if secret == secret[::-1]:  # 回文
            return False, "密鑰不應是回文結構"
        
        # 檢查重複字符
        for i in range(len(secret) - 3):
            if secret[i] == secret[i+1] == secret[i+2]:
                return False, "密鑰包含過多重複字符"
        
        return True, ""


# 全局實例
_secret_manager_instance: Optional[SecretManager] = None


def get_secret_manager() -> SecretManager:
    """獲取密鑰管理器的全局實例（單例模式）"""
    global _secret_manager_instance
    
    if _secret_manager_instance is None:
        _secret_manager_instance = SecretManager()
    
    return _secret_manager_instance
