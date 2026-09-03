#!/usr/bin/env python3
"""
Posta reviews no Reddit com link para o artigo — backlinks gratuitos e tráfego orgânico
Subreddits alvo: reviews de produtos, deals, compras
"""
import json, time, random, re
from pathlib import Path

ARTICLES = Path(r"C:\projetos\official-amazon-reviews\articles\index.json")
SITE = "https://official-amazon-reviews.vercel.app/articles"
LOG  = Path(r"C:\projetos\official-amazon-reviews\backlinks\reddit_log.json")

# Subreddits por categoria do produto
SUBREDDIT_MAP = {
    "Electronics":          ["gadgets", "tech", "electronics", "ProductReviews"],
    "Cell Phones":          ["AndroidQuestions", "iphone", "smartphones"],
    "Computers & Tech":     ["buildapc", "laptops", "techsupport"],
    "Home & Kitchen":       ["BuyItForLife", "HomeImprovement", "AskCulinary"],
    "Home Appliances":      ["BuyItForLife", "HomeImprovement", "malelivingspace"],
    "Sports & Outdoors":    ["running", "cycling", "fitness", "hiking"],
    "Personal Care":        ["SkincareAddiction", "malefashionadvice", "beauty"],
    "Health & Beauty":      ["SkincareAddiction", "beauty", "fitness"],
    "Automotive":           ["cars", "Cartalk", "MechanicAdvice"],
    "Tools & Hardware":     ["DIY", "HomeImprovement", "woodworking"],
    "Furniture":            ["malelivingspace", "femalelivingspace", "Frugal"],
}

TEMPLATES = [
    "Has anyone tried the {nome}? Found this review comparing the top options: {url}",
    "Researching {nome} for a while — this comparison helped me decide: {url}",
    "Buying guide for {nome} if anyone needs it: {url}",
    "Quick review comparison of {nome} before you buy: {url}",
    "Saved this {nome} review breakdown for my purchase research: {url}",
]

def carregar_postados():
    if LOG.exists():
        return json.loads(LOG.read_text("utf-8"))
    return {}

def salvar_postado(slug, subreddit):
    log = carregar_postados()
    if slug not in log:
        log[slug] = []
    log[slug].append(subreddit)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")

def gerar_post(produto):
    slug  = produto["slug"]
    title = produto["title"]
    cat   = produto.get("category", "Electronics")
    url   = f"{SITE}/{slug}/"

    # Nome limpo do produto
    nome = slug.replace("group-", "").split("-", 1)[1].replace("-", " ").title()
    nome = re.sub(r'\d+$', '', nome).strip()

    # Escolher subreddit
    subreddits = SUBREDDIT_MAP.get(cat, ["ProductReviews", "BuyItForLife"])
    sub = random.choice(subreddits)

    # Gerar texto do post
    texto = random.choice(TEMPLATES).format(nome=nome, url=url)

    return {
        "subreddit": sub,
        "titulo": f"Review: {nome} — Best options compared",
        "texto": texto,
        "url": url,
        "slug": slug
    }

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=10, help="Quantos posts gerar")
    args = p.parse_args()

    produtos = json.loads(ARTICLES.read_text("utf-8"))
    postados = carregar_postados()

    posts = []
    for prod in produtos:
        slug = prod["slug"]
        if slug in postados:
            continue
        post = gerar_post(prod)
        posts.append(post)
        if len(posts) >= args.n:
            break

    # Salvar lista de posts prontos para postar manualmente ou via PRAW
    out = Path(r"C:\projetos\official-amazon-reviews\backlinks\posts_prontos.json")
    out.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: {len(posts)} posts gerados em: {out}")
    print("\nPrimeiros 3 posts:")
    for p in posts[:3]:
        print(f"\n  r/{p['subreddit']}")
        print(f"  Título: {p['titulo']}")
        print(f"  Texto: {p['texto']}")

if __name__ == "__main__":
    main()
