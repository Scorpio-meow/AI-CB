
import os
import secrets
import logging
import hashlib
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
import json
logger = logging.getLogger(__name__)
class SecretManager:
    
    def __init__(self, secrets_file: str = "secrets.enc"):
        self.secrets_file = Path(secrets_file)
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        key_env = os.getenv("SECRETS_ENCRYPTION_KEY")
        
        if key_env:
            try:
                return key_env.encode('utf-8')
            except Exception:
                logger.warning("環境變數中的加密密鑰格式不正確")
        
        new_key = Fernet.generate_key()
        digest = hashlib.sha256(new_key).hexdigest()[:8]
        logger.warning(
            "未找到 SECRETS_ENCRYPTION_KEY 環境變數\n"
            "已生成新的加密密鑰（摘要）: %s\n"
            "請將此密鑰添加到環境變數中以保證數據持久性",
            digest
        )
        return new_key
    
    def get_or_generate_secret(
        self, 
        key_name: str, 
        length: int = 32,
        force_regenerate: bool = False
    ) -> str:
        if not force_regenerate:
            secret = os.getenv(key_name)
            if secret:
                logger.info(f"從環境變數載入密鑰: {key_name}")
                return secret
        
        if not force_regenerate and self.secrets_file.exists():
            secret = self._load_from_encrypted_file(key_name)
            if secret:
                logger.info(f"從加密文件載入密鑰: {key_name}")
                return secret
        
        new_secret = secrets.token_urlsafe(length)
        self._save_to_encrypted_file(key_name, new_secret)
        
        try:
            secret_digest = hashlib.sha256(new_secret.encode('utf-8')).hexdigest()[:8]
        except Exception:
            secret_digest = 'unknown'
        logger.warning(
            "生成新的 %s，並已加密保存。請將此密鑰添加到 .env 文件中以便持久化",
            key_name
        )
        
        return new_secret
    
    def _load_from_encrypted_file(self, key_name: str) -> Optional[str]:
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
        try:
            secrets_dict = {}
            if self.secrets_file.exists():
                try:
                    with open(self.secrets_file, 'rb') as f:
                        encrypted_data = f.read()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    secrets_dict = json.loads(decrypted_data.decode('utf-8'))
                except Exception:
                    pass
            
            secrets_dict[key_name] = value
            
            data_to_encrypt = json.dumps(secrets_dict).encode('utf-8')
            encrypted_data = self.cipher.encrypt(data_to_encrypt)
            
            with open(self.secrets_file, 'wb') as f:
                f.write(encrypted_data)
            
            if os.name != 'nt':
                os.chmod(self.secrets_file, 0o600)
            
            logger.info(f"密鑰 {key_name} 已加密保存")
        
        except Exception as e:
            logger.error(f"保存密鑰失敗: {e}")
    
    def rotate_secret(self, key_name: str, length: int = 32) -> str:
        old_secret = self.get_or_generate_secret(key_name, length)
        self._save_to_encrypted_file(f"{key_name}_OLD", old_secret)
        
        new_secret = self.get_or_generate_secret(key_name, length, force_regenerate=True)
        
        logger.info(f"密鑰 {key_name} 已輪換，舊密鑰保存為 {key_name}_OLD")
        
        return new_secret
    
    def validate_secret_strength(self, secret: str) -> tuple[bool, str]:
        if len(secret) < 32:
            return False, "密鑰長度至少需要 32 個字符"
        
        has_upper = any(c.isupper() for c in secret)
        has_lower = any(c.islower() for c in secret)
        has_digit = any(c.isdigit() for c in secret)
        
        if not (has_upper and has_lower and has_digit):
            return False, "密鑰應包含大寫字母、小寫字母和數字"
        
        if secret == secret[::-1]:
            return False, "密鑰不應是回文結構"
        
        for i in range(len(secret) - 3):
            if secret[i] == secret[i+1] == secret[i+2]:
                return False, "密鑰包含過多重複字符"
        
        return True, ""
_secret_manager_instance: Optional[SecretManager] = None
def get_secret_manager() -> SecretManager:
    global _secret_manager_instance
    
    if _secret_manager_instance is None:
        _secret_manager_instance = SecretManager()
    
    return _secret_manager_instance
