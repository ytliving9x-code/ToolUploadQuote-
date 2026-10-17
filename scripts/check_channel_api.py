import requests
import json

# Thử qua các dịch vụ phân tích TikTok công khai
endpoints = [
    "https://api.countik.com/user/@promisdaxix",
    "https://tokcounter.com/api/user/promisdaxix",
]

for ep in endpoints:
    try:
        res = requests.get(ep, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        print(ep, "Status:", res.status_code)
        if res.status_code == 200:
            print(res.text[:500])
    except Exception as e:
        print(ep, "Error:", e)
