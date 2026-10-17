import urllib.request
import re

url = "https://urlebird.com/user/promisdaxix/"
req = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="ignore")
        titles = re.findall(r"<title>(.*?)</title>", html, re.I)
        print("Title:", titles)
        # Find video descriptions / captions
        captions = re.findall(r"class=[\"']info2[\"'][^>]*>(.*?)</div>", html, re.DOTALL)
        if not captions:
            captions = re.findall(r"alt=[\"'](.*?)[\"']", html)
        print("Captions / Alts sample:", captions[:5])
        # Find music names
        music = re.findall(r"music-title.*?>(.*?)<", html)
        print("Music:", music[:5])
except Exception as e:
    print("Error:", e)
