
import os
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
class RSAKeyManager:
    
    def __init__(self, keys_dir: str = "keys"):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(exist_ok=True)
        
        self.private_key_path = self.keys_dir / "jwt_private.pem"
        self.public_key_path = self.keys_dir / "jwt_public.pem"
        
        if not self.keys_exist():
            self.generate_keys()
    
    def keys_exist(self) -> bool:
        return self.private_key_path.exists() and self.public_key_path.exists()
    
    def generate_keys(self, key_size: int = 2048):
        print(f"🔐 生成 RSA 金鑰對 ({key_size} bits)...")
        
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        with open(self.private_key_path, 'wb') as f:
            f.write(private_pem)
        
        os.chmod(self.private_key_path, 0o600)
        
        public_key = private_key.public_key()
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(self.public_key_path, 'wb') as f:
            f.write(public_pem)
        
        print(f"✅ RSA 金鑰對已生成:")
        print(f"   私鑰: {self.private_key_path}")
        print(f"   公鑰: {self.public_key_path}")
    
    def load_private_key(self):
        with open(self.private_key_path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    def load_public_key(self):
        with open(self.public_key_path, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    
    def get_private_key_pem(self) -> str:
        with open(self.private_key_path, 'r') as f:
            return f.read()
    
    def get_public_key_pem(self) -> str:
        with open(self.public_key_path, 'r') as f:
            return f.read()
rsa_manager = RSAKeyManager(keys_dir=os.path.join(os.path.dirname(__file__), "..", "..", "keys"))
