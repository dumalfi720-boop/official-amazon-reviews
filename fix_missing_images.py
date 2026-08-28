import re

fixes = {
    "group-1-12-inch-mobile-screen-magnifier": "https://m.media-amazon.com/images/I/41Sea9NpbfL._AC_.jpg",
    "group-2-hp-zbook-fury-g1i": "https://m.media-amazon.com/images/I/71o4tPEFqIL._AC_SL1500_.jpg",
}

base = r"C:\projetos\official-amazon-reviews\articles"

for group, img_url in fixes.items():
    path = f"{base}\\{group}\\index.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Substituir todos os placehold.co por imagem real
    content = re.sub(r'https://placehold\.co/[^"]+', img_url, content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Corrigido: {group}")

print("Pronto!")
