import requests
import json

url = "https://1848b1fg-8001.asse.devtunnels.ms/api/auth/login"
origin = "https://1848b1fg-3000.asse.devtunnels.ms"

print(f"測試登入 URL: {url}")
print(f"Origin: {origin}\n")

headers = {
    "Origin": origin,
    "Content-Type": "application/json",
}

data = {
    "username": "yaikyao@mitac.com.tw",
    "password": "test"  # 請改成實際密碼
}

print("發送登入請求...")
try:
    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=30  # 30秒超時
    )
    
    print(f"\n狀態碼: {response.status_code}")
    print(f"回應時間: {response.elapsed.total_seconds():.2f} 秒")
    
    # 檢查 CORS
    cors_header = response.headers.get('Access-Control-Allow-Origin', '未設定')
    print(f"CORS Header: {cors_header}")
    
    # 打印回應內容
    print(f"\n回應內容:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("\n❌ 請求超時！後端沒有在 30 秒內回應")
    print("\n可能的原因：")
    print("1. 後端正在處理其他耗時操作（如初始化 RAG 系統）")
    print("2. 後端的某個中間件或依賴卡住了")
    print("3. 資料庫查詢或密碼驗證卡住")
    
except Exception as e:
    print(f"\n❌ 請求失敗: {type(e).__name__}: {e}")
