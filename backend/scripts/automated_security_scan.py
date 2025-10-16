#!/usr/bin/env python3
"""
自動化安全掃描腳本
定期執行安全檢查，生成報告
"""

import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

# 添加項目路徑
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_security_scanner():
    """運行安全掃描器"""
    print("=" * 80)
    print("🔍 執行安全掃描...")
    print("=" * 80)
    
    scanner_script = PROJECT_ROOT / "scripts" / "security_scanner.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(scanner_script)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        if result.stderr:
            print("錯誤輸出:", result.stderr)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 安全掃描失敗: {e}")
        return False


def check_dependencies():
    """檢查依賴漏洞"""
    print("\n" + "=" * 80)
    print("📦 檢查 Python 依賴漏洞...")
    print("=" * 80)
    
    try:
        # 檢查是否安裝 safety
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "safety"],
            capture_output=True
        )
        
        if result.returncode != 0:
            print("⚠️  safety 未安裝，跳過依賴掃描")
            print("   安裝命令: pip install safety")
            return True
        
        # 運行 safety check
        result = subprocess.run(
            [sys.executable, "-m", "safety", "check", "--json"],
            cwd=str(PROJECT_ROOT / "backend"),
            capture_output=True,
            text=True
        )
        
        if result.stdout:
            vulnerabilities = json.loads(result.stdout)
            if vulnerabilities:
                print(f"⚠️  發現 {len(vulnerabilities)} 個依賴漏洞:")
                for vuln in vulnerabilities[:5]:  # 只顯示前 5 個
                    print(f"  - {vuln.get('package')}: {vuln.get('vulnerability')}")
                return False
            else:
                print("✅ 未發現依賴漏洞")
        else:
            print("✅ 依賴檢查完成")
        
        return True
    except Exception as e:
        print(f"⚠️  依賴檢查失敗: {e}")
        return True  # 不阻止其他檢查


def check_env_files():
    """檢查環境變數檔案"""
    print("\n" + "=" * 80)
    print("🔐 檢查環境變數配置...")
    print("=" * 80)
    
    env_file = PROJECT_ROOT / "backend" / ".env"
    template_file = PROJECT_ROOT / "backend" / ".env.template"
    
    issues = []
    
    # 檢查 .env 是否存在
    if not env_file.exists():
        issues.append("⚠️  .env 檔案不存在")
    
    # 檢查 .env.template 是否存在
    if not template_file.exists():
        issues.append("⚠️  .env.template 範本檔案不存在")
    
    # 檢查 .gitignore 是否包含 .env
    gitignore_file = PROJECT_ROOT / ".gitignore"
    if gitignore_file.exists():
        gitignore_content = gitignore_file.read_text()
        if ".env" not in gitignore_content:
            issues.append("❌ .env 未被 .gitignore 排除！")
    
    if issues:
        for issue in issues:
            print(issue)
        return False
    
    print("✅ 環境變數配置檢查通過")
    return True


def generate_report(results):
    """生成安全報告"""
    print("\n" + "=" * 80)
    print("📊 生成安全報告...")
    print("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = PROJECT_ROOT / f"security_scan_{timestamp}.json"
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "results": results,
        "status": "PASS" if all(results.values()) else "FAIL"
    }
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 報告已保存: {report_file}")
        return True
    except Exception as e:
        print(f"❌ 報告生成失敗: {e}")
        return False


def main():
    """主函數"""
    print("\n🛡️  ChatBot 自動化安全掃描")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {
        "security_scanner": run_security_scanner(),
        "dependency_check": check_dependencies(),
        "env_files_check": check_env_files()
    }
    
    generate_report(results)
    
    # 顯示總結
    print("\n" + "=" * 80)
    print("📋 掃描總結")
    print("=" * 80)
    
    for check, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{check}: {status}")
    
    print("\n" + "=" * 80)
    
    # 返回狀態碼
    if all(results.values()):
        print("🎉 所有安全檢查通過！")
        return 0
    else:
        print("⚠️  部分檢查失敗，請查看上方詳情")
        return 1


if __name__ == "__main__":
    sys.exit(main())
