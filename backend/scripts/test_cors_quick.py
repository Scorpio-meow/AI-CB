import requests

url = "https://1848b1fg-8001.asse.devtunnels.ms/health"
origin = "https://1848b1fg-3000.asse.devtunnels.ms"

print(f"測試 URL: {url}")
print(f"Origin: {origin}\n")

# 測試帶 Origin header
headers = {"Origin": origin}
response = requests.get(url, headers=headers)

print(f"狀態碼: {response.status_code}")
print(f"\n=== 回應 Headers ===")
for key, value in response.headers.items():
    if 'access-control' in key.lower() or 'cors' in key.lower():
        print(f"  {key}: {value}")

# 檢查是否有 CORS header
if 'Access-Control-Allow-Origin' in response.headers:
    print(f"\n✅ CORS 配置正確")
else:
    print(f"\n❌ 缺少 Access-Control-Allow-Origin header!")
    print("\n可能的原因：")
    print("1. 後端 .env 中的 ENVIRONMENT 沒有設定或不是 'development'")
    print("2. 後端 .env 中的 ALLOWED_ORIGIN_REGEX 沒有匹配到該 Origin")
    print("3. 後端需要重新啟動以載入 .env 變更")
