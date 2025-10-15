#!/usr/bin/env python3
"""
快速安全檢查腳本
執行所有必要的安全檢查
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """執行命令並顯示結果"""
    print(f"\n{'='*80}")
    print(f"🔍 {description}")
    print(f"{'='*80}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        return False

def main():
    """主函數"""
    print("\n" + "="*80)
    print("🛡️  ChatBot 專案安全檢查")
    print("="*80)
    
    script_dir = Path(__file__).parent
    backend_dir = script_dir.parent
    
    checks = []
    
    # 1. 檢查敏感文件是否被 git 追蹤
    print("\n📋 檢查 1/4: Git 敏感文件保護")
    result = subprocess.run(
        'git ls-files | findstr /I ".env"',
        shell=True,
        capture_output=True,
        text=True,
        cwd=backend_dir.parent
    )
    
    if result.stdout.strip():
        print(f"⚠️  警告: 發現被追蹤的 .env 文件:\n{result.stdout}")
        print("   請執行: git rm --cached backend/.env")
        checks.append(False)
    else:
        print("✅ .env 文件已正確忽略")
        checks.append(True)
    
    # 2. 檢查 RSA 金鑰
    print("\n📋 檢查 2/4: RSA 金鑰")
    keys_dir = backend_dir / 'keys'
    private_key = keys_dir / 'jwt_private.pem'
    public_key = keys_dir / 'jwt_public.pem'
    
    if private_key.exists() and public_key.exists():
        print("✅ RSA 金鑰已存在")
        checks.append(True)
    else:
        print("⚠️  警告: RSA 金鑰不存在，將在啟動時自動生成")
        checks.append(True)  # 不算錯誤
    
    # 3. 運行安全掃描
    print("\n📋 檢查 3/4: 安全掃描")
    scanner_path = script_dir / 'security_scanner.py'
    if scanner_path.exists():
        result = run_command(
            f'python "{scanner_path}"',
            "執行安全掃描"
        )
        checks.append(result)
    else:
        print("⚠️  安全掃描腳本不存在")
        checks.append(False)
    
    # 4. 運行安全測試
    print("\n📋 檢查 4/4: 安全測試")
    test_file = backend_dir / 'tests' / 'test_security.py'
    if test_file.exists():
        result = run_command(
            f'cd "{backend_dir}" && pytest "{test_file}" -v --tb=short',
            "執行安全測試"
        )
        checks.append(result)
    else:
        print("⚠️  安全測試文件不存在")
        checks.append(False)
    
    # 總結
    print("\n" + "="*80)
    print("📊 安全檢查摘要")
    print("="*80)
    
    passed = sum(checks)
    total = len(checks)
    
    print(f"\n通過: {passed}/{total}")
    
    if passed == total:
        print("\n✅ 所有安全檢查通過！")
        print("🎉 專案已準備好部署到測試環境")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 項檢查失敗")
        print("請查看上述錯誤並修復")
        return 1

if __name__ == '__main__':
    sys.exit(main())
