"""
RSA 金鑰管理
用於 JWT 非對稱加密簽名
"""

import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


class RSAKeyManager:
    """RSA 金鑰管理器"""
    
    def __init__(self, keys_dir: str = "keys"):
        """
        初始化 RSA 金鑰管理器
        
        Args:
            keys_dir: 金鑰儲存目錄
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(exist_ok=True)
        
        self.private_key_path = self.keys_dir / "jwt_private.pem"
        self.public_key_path = self.keys_dir / "jwt_public.pem"
        
        # 確保金鑰存在
        if not self.keys_exist():
            self.generate_keys()
    
    def keys_exist(self) -> bool:
        """檢查金鑰是否存在"""
        return self.private_key_path.exists() and self.public_key_path.exists()
    
    def generate_keys(self, key_size: int = 2048):
        """
        生成 RSA 金鑰對
        
        Args:
            key_size: 金鑰大小（位元）
        """
        print(f"🔐 生成 RSA 金鑰對 ({key_size} bits)...")
        
        # 生成私鑰
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # 序列化私鑰（PEM 格式）
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # 儲存私鑰
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)
        
        # 設置私鑰檔案權限（僅擁有者可讀寫）
        os.chmod(self.private_key_path, 0o600)
        
        # 生成公鑰
        public_key = private_key.public_key()
        
        # 序列化公鑰（PEM 格式）
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # 儲存公鑰
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)
        
        print(f"✅ RSA 金鑰對已生成:")
        print(f"   私鑰: {self.private_key_path}")
        print(f"   公鑰: {self.public_key_path}")
    
    def load_private_key(self):
        """載入私鑰"""
        with open(self.private_key_path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def load_public_key(self):
        """載入公鑰"""
        with open(self.public_key_path, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    
    def get_private_key_pem(self) -> str:
        """獲取私鑰 PEM 字符串"""
        with open(self.private_key_path, 'r') as f:
            return f.read()
    
    def get_public_key_pem(self) -> str:
        """獲取公鑰 PEM 字符串"""
        with open(self.public_key_path, 'r') as f:
            return f.read()


# 全局 RSA 金鑰管理器實例
rsa_manager = RSAKeyManager(keys_dir=os.path.join(os.path.dirname(__file__), "..", "..", "keys"))
