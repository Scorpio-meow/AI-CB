import requests
url = "https://blowfish-absolute-absolutely.ngrok-free.app/api/tags"
r = requests.get(url, headers={"ngrok-skip-browser-warning":"true"}, timeout=10)
print(r.status_code)
print(r.headers.get("content-type"))
print(r.text[:1000])