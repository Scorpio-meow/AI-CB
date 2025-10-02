import requests
import json

# 測試從 DevTunnels 前端訪問後端 API
BACKEND_URL = "https://1848b1fg-8001.asse.devtunnels.ms"
FRONTEND_ORIGIN = "https://1848b1fg-3000.asse.devtunnels.ms"

print(f"測試後端 URL: {BACKEND_URL}")
print(f"模擬來源 (Origin): {FRONTEND_ORIGIN}")
print("-" * 60)

# 1. 測試 health endpoint
print("\n1. 測試 /health 端點...")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=10)
    print(f"   狀態碼: {response.status_code}")
    print(f"   回應: {response.json()}")
except Exception as e:
    print(f"   ❌ 錯誤: {e}")

# 2. 測試 CORS preflight (OPTIONS request)
print("\n2. 測試 CORS preflight (OPTIONS /api/auth/login)...")
try:
    headers = {
        'Origin': FRONTEND_ORIGIN,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'content-type',
    }
    response = requests.options(f"{BACKEND_URL}/api/auth/login", headers=headers, timeout=10)
    print(f"   狀態碼: {response.status_code}")
    print(f"   CORS Headers:")
    for header in ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers', 'Access-Control-Allow-Credentials']:
        value = response.headers.get(header, '未設定')
        print(f"      {header}: {value}")
except Exception as e:
    print(f"   ❌ 錯誤: {e}")

# 3. 測試實際登入請求 (帶 Origin header)
print("\n3. 測試 POST /api/auth/login (帶 Origin header)...")
try:
    headers = {
        'Origin': FRONTEND_ORIGIN,
        'Content-Type': 'application/json',
    }
    data = {
        'email': 'test@example.com',
        'password': 'testpassword'
    }
    response = requests.post(
        f"{BACKEND_URL}/api/auth/login",
        headers=headers,
        json=data,
        timeout=10
    )
    print(f"   狀態碼: {response.status_code}")
    print(f"   CORS Header (Allow-Origin): {response.headers.get('Access-Control-Allow-Origin', '未設定')}")
    if response.status_code < 500:
        try:
            print(f"   回應內容: {response.json()}")
        except:
            print(f"   回應內容: {response.text[:200]}")
except Exception as e:
    print(f"   ❌ 錯誤: {e}")

print("\n" + "=" * 60)
print("測試完成")
