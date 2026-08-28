"""
IndexNow — submete todas as URLs do site para indexação imediata
Funciona com: Bing, Yandex, Seznam, Naver
"""
import json
import urllib.request
import urllib.error
import time

SITE = "https://official-amazon-reviews.vercel.app"
API_KEY = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"  # gerar chave unica
KEY_LOCATION = f"{SITE}/{API_KEY}.txt"

# Carregar URLs do sitemap local
import xml.etree.ElementTree as ET
tree = ET.parse(r"C:\projetos\official-amazon-reviews\sitemap.xml")
root = tree.getroot()
ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [loc.text for loc in root.findall("s:url/s:loc", ns)]
print(f"URLs carregadas: {len(urls)}")

# Submeter em lotes de 10000 (limite IndexNow)
payload = {
    "host": "official-amazon-reviews.vercel.app",
    "key": API_KEY,
    "keyLocation": KEY_LOCATION,
    "urlList": urls
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=data,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow status: {r.status}")
        print(f"Resposta: {r.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"IndexNow status: {e.code}")
    print(f"Resposta: {e.read().decode()}")
except Exception as e:
    print(f"Erro: {e}")
