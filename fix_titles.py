import os
import re

ARTICLES_PATH = r"C:\projetos\official-amazon-reviews\articles"

MAP = {
    "Esportes e Aventura":         "Sports & Outdoors",
    "Informatica":                 "Computers & Tech",
    "Casa e Cozinha":              "Home & Kitchen",
    "Celulares e Telefonia":       "Cell Phones & Accessories",
    "Eletronicos":                 "Electronics",
    "Higiene e Cuidados Pessoais": "Personal Care",
    "Eletrodomesticos":            "Home Appliances",
    "Ferramentas e Construcao":    "Tools & Hardware",
    "Automotivo":                  "Automotive",
    "Saude e Beleza":              "Health & Beauty",
    "Moveis":                      "Furniture",
}

# Encoding broken sequences (UTF-8 bytes read as Latin-1)
ENCODING_FIXES = [
    ("â€“", "–"),  # â€" -> en dash
    ("â€”", "—"),  # â€" -> em dash
    ("â€™", "’"),  # â€™ -> right single quote
    ("â€œ", "“"),  # â€œ -> left double quote
    ("â€", "”"),  # â€ -> right double quote
    ("Ã§", "c"),             # Ã§ -> c
    ("Ã£", "a"),             # Ã£ -> a
    ("Ã¢", "a"),             # Ã¢ -> a
]

fixed = 0
errors = 0

for folder in os.listdir(ARTICLES_PATH):
    filepath = os.path.join(ARTICLES_PATH, folder, "index.html")
    if not os.path.exists(filepath):
        continue
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original = content

        # Fix encoding
        for broken, correct in ENCODING_FIXES:
            content = content.replace(broken, correct)

        # Fix categories PT -> EN
        for pt, en in MAP.items():
            content = content.replace(pt, en)

        if content != original:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            fixed += 1
    except Exception as e:
        errors += 1
        print(f"ERRO: {folder} - {e}")

print(f"Arquivos corrigidos: {fixed}")
print(f"Erros: {errors}")
