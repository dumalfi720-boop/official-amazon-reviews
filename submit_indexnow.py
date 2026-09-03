"""
IndexNow — submete todas as URLs do site para indexação imediata
Funciona com: Bing, Yandex, Seznam, Naver
"""
import json
import urllib.request
import urllib.error
import time
import xml.etree.ElementTree as ET

SITE = "https://official-amazon-reviews.vercel.app"
API_KEY = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
KEY_LOCATION = f"{SITE}/{API_KEY}.txt"

# Carregar URLs do sitemap
tree = ET.parse(r"C:\projetos\official-amazon-reviews\sitemap.xml")
root = tree.getroot()
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [loc.text for loc in root.findall("s:url/s:loc", ns)]
print(f"URLs carregadas: {len(urls)}")

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]

# Submeter em lotes de 100
BATCH = 100
for endpoint in ENDPOINTS:
    print(f"\nSubmetendo para: {endpoint}")
    for i in range(0, len(urls), BATCH):
        batch = urls[i:i+BATCH]
        payload = {
            "host": "official-amazon-reviews.vercel.app",
            "key": API_KEY,
            "keyLocation": KEY_LOCATION,
            "urlList": batch
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint, data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                print(f"  Lote {i//BATCH+1}: {r.status} OK ({len(batch)} URLs)")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  Lote {i//BATCH+1}: {e.code} - {body[:80]}")
        except Exception as ex:
            print(f"  Lote {i//BATCH+1}: erro - {ex}")
        time.sleep(1)
    print(f"  Concluido!")
