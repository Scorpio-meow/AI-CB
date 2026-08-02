import sys
import requests
import json
from datetime import datetime
def check_health():
    try:
        import os
        base_url = os.getenv('BASE_URL')
        host = os.getenv('HOST')
        port = os.getenv('PORT')
        if base_url:
            base = base_url.rstrip('/')
        elif host and port:
            base = f"http://{host}:{port}"
        else:
            raise RuntimeError("healthcheck requires BASE_URL or both HOST and PORT environment variables to be set.")
        response = requests.get(f"{base}/", timeout=5)
        
        if response.status_code != 200:
            print(f"ERROR: API 返回狀態碼 {response.status_code}")
            return False
            
        try:
            db_response = requests.get(f"{base}/api/admin/stats", timeout=5)
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
        sys.exit(0)
    else:
        sys.exit(1)
