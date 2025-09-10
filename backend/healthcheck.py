#!/usr/bin/env python3
"""
健康檢查腳本 - 用於 Docker 容器健康檢查
"""

import sys
import requests
import json
from datetime import datetime

def check_health():
    """檢查應用程式健康狀態"""
    try:
        # 檢查基本 API 端點
        response = requests.get("http://localhost:8001/", timeout=5)
        
        if response.status_code != 200:
            print(f"ERROR: API 返回狀態碼 {response.status_code}")
            return False
            
        # 檢查資料庫連接
        try:
            db_response = requests.get("http://localhost:8001/api/admin/stats", timeout=5)
            if db_response.status_code != 200:
                print("WARNING: 資料庫連接可能有問題")
        except Exception as e:
            print(f"WARNING: 無法檢查資料庫狀態: {e}")
            
        print(f"✅ 健康檢查通過 - {datetime.now()}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: 無法連接到應用程式: {e}")
        return False
    except Exception as e:
        print(f"ERROR: 健康檢查失敗: {e}")
        return False

if __name__ == "__main__":
    if check_health():
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失敗
