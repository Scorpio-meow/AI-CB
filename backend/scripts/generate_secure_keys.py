#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全密鑰生成工具
用於生成高強度的 API Key、JWT Secret 等
"""

import secrets
import string
from pathlib import Path

def generate_api_key(length: int = 64) -> str:
    """
    生成高強度 API Key
    
    Args:
        length: 密鑰長度（建議至少 64）
        
    Returns:
        隨機生成的 API Key
    """
    alphabet = string.ascii_letters + string.digits + '_-'
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_jwt_secret(length: int = 64) -> str:
    """
    生成 JWT Secret Key
    使用 URL-safe base64 編碼
    
    Args:
        length: 密鑰長度（字節數）
        
    Returns:
        URL-safe base64 編碼的密鑰
    """
    return secrets.token_urlsafe(length)

def generate_all_keys():
    """生成所有必要的密鑰"""
    keys = {
        'ADMIN_API_KEY': generate_api_key(64),
        'JWT_SECRET_KEY': generate_jwt_secret(64),
        'SECRET_KEY': generate_jwt_secret(64),
    }
    
    print("=" * 80)
    print("🔐 安全密鑰生成完成")
    print("=" * 80)
    print("\n請將以下內容更新到您的 backend/.env 文件中：\n")
    
    for key_name, key_value in keys.items():
        print(f"{key_name}={key_value}")
    
    print("\n" + "=" * 80)
    print("⚠️  重要提醒：")
    print("1. 請立即更新 .env 文件")
    print("2. 確保 .env 文件已加入 .gitignore")
    print("3. 不要將這些密鑰提交到版本控制")
    print("4. 定期輪換密鑰（建議每 90 天）")
    print("=" * 80)
    
    # 保存到臨時文件（供參考）
    output_file = Path(__file__).parent / 'generated_keys.txt'
    with open(output_file, 'w') as f:
        f.write("# 生成的安全密鑰 - 請立即複製並刪除此文件\n")
        f.write("# 生成時間: 2025-10-15\n\n")
        for key_name, key_value in keys.items():
            f.write(f"{key_name}={key_value}\n")
    
    print(f"\n密鑰已保存到: {output_file}")
    print("請在複製後立即刪除此文件！\n")

if __name__ == '__main__':
    generate_all_keys()
