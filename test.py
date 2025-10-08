import requests
import json

url = "https://blowfish-absolute-absolutely.ngrok-free.app/api/generate"
data = {
    "model": "granite4:small-h",
    "prompt": "你是神通資訊科技內部的知識型助理...",
    "stream": False
}

response = requests.post(url, json=data)
print(response.json())
