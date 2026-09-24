#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_artigos_letra_D_us.py - Gera artigos HTML via OpenRouter para keywords aprovadas LETRA D.

Uso:
  python gerar_artigos_letra_D_us.py --n 10       # testa com 10 artigos
  python gerar_artigos_letra_D_us.py              # processa todos aprovados
  python gerar_artigos_letra_D_us.py --dry        # lista sem criar
  python gerar_artigos_letra_D_us.py --skip-ai    # gera com conteudo placeholder (sem IA)
  python gerar_artigos_letra_D_us.py --force      # sobrescreve artigos existentes
"""

import json, re, sys, time, subprocess, argparse, urllib.request, urllib.parse, os
from pathlib import Path
from datetime import date

_env_path = Path(r"C:\projetos\semrush-central\alfabeto\.env")
if _env_path.exists():
    for line in _env_path.read_text('utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

RESULTADO_JSON = Path(__file__).parent / "D_resultado_us.json"
ART_DIR   = Path(r"C:\projetos\official-amazon-reviews\articles")
INDEX_JSON = ART_DIR / "index.json"
SITE_URL  = "https://official-reviews-product.vercel.app"
TODAY     = date.today().isoformat()


def extrair_keywords_aprovadas() -> dict:
    """Extrai produtos com keywords aprovadas de D_resultado_us.json"""
    if not RESULTADO_JSON.exists():
        print(f"❌ Arquivo não encontrado: {RESULTADO_JSON}")
        return {}

    data = json.loads(RESULTADO_JSON.read_text('utf-8'))
    produtos_com_keywords = {}

    for item in data:
        if item['aprovados']:
            num = item['num']
            produto = item['produto']
            produtos_com_keywords[f"d_{num:03d}_{produto.lower().replace(' ','-')}"] = {
                'num': num,
                'produto': produto,
                'keywords': item['aprovados']
            }

    return produtos_com_keywords


def gerar_conteudo_ia(produto: str, keywords: list) -> str:
    """Gera conteúdo com OpenRouter (Nemotron)"""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return f"<p>Content for {produto} with keywords: {', '.join(k['keyword'] for k in keywords)}</p>"

    kw_list = ', '.join([k['keyword'] for k in keywords[:3]])
    prompt = f"""Write a professional 500-word Amazon product review article for: {produto}
Focus on keywords: {kw_list}
Include: benefits, features, FAQs, affiliate link opportunity.
HTML format with h2/h3 headings. Engaging, SEO-friendly."""

    try:
        payload = {
            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            result = json.loads(r.read().decode('utf-8'))
            return result['choices'][0]['message']['content']
    except Exception as e:
        print(f"⚠️  Erro IA para {produto}: {e}")
        return f"<p>Review of {produto}. Keywords: {kw_list}</p>"


def gerar_html_artigo(produto: str, keywords: list, conteudo_ia: str = None) -> str:
    """Gera HTML completo do artigo"""
    kw_principal = keywords[0]['keyword'] if keywords else produto

    if conteudo_ia:
        corpo = conteudo_ia
    else:
        corpo = f"<h2>Overview of {produto}</h2><p>This comprehensive review covers {produto}...</p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{kw_principal} - Best Reviews 2026</title>
    <meta name="description" content="Expert review of {produto}. Compare features, prices & more.">
</head>
<body>
    <article>
        <h1>{kw_principal}</h1>
        {corpo}
        <p><a href="https://amazon.com/s?k={urllib.parse.quote(produto)}&tag=1326-20">View on Amazon</a></p>
    </article>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--n', type=int, default=None, help='Limitar a N artigos')
    parser.add_argument('--dry', action='store_true', help='Listar sem criar')
    parser.add_argument('--skip-ai', action='store_true', help='Sem IA (placeholder)')
    parser.add_argument('--force', action='store_true', help='Sobrescrever existentes')
    args = parser.parse_args()

    produtos = extrair_keywords_aprovadas()
    if not produtos:
        print("❌ Nenhum produto com keywords aprovadas encontrado")
        return

    print(f"\n📊 LETRA D - GERAÇÃO DE ARTIGOS")
    print(f"{'='*60}")
    print(f"Total de produtos com keywords: {len(produtos)}")

    if args.dry:
        print(f"\n📋 Produtos a processar:")
        for idx, (slug, info) in enumerate(produtos.items(), 1):
            print(f"  {idx:2d}. {info['produto']:<35} ({len(info['keywords'])} keywords)")
        return

    processados = 0
    criados = 0

    for slug, info in list(produtos.items())[:args.n or len(produtos)]:
        art_path = ART_DIR / slug
        if art_path.exists() and not args.force:
            print(f"⏭️  [{processados+1:2d}] {info['produto']:<35} (já existe)")
            processados += 1
            continue

        print(f"⏳ [{processados+1:2d}] {info['produto']:<35} gerando...", end=" ", flush=True)

        conteudo = None if args.skip_ai else gerar_conteudo_ia(info['produto'], info['keywords'])
        html = gerar_html_artigo(info['produto'], info['keywords'], conteudo)

        art_path.mkdir(parents=True, exist_ok=True)
        (art_path / "index.html").write_text(html, encoding='utf-8')

        meta = {
            "id": slug,
            "produto": info['produto'],
            "keywords": info['keywords'],
            "data": TODAY,
            "letra": "D"
        }
        (art_path / "meta.json").write_text(json.dumps(meta, indent=2), encoding='utf-8')

        print("✅")
        criados += 1
        processados += 1
        time.sleep(1)

    print(f"\n{'='*60}")
    print(f"✅ Artigos criados: {criados}/{processados}")


if __name__ == "__main__":
    main()
