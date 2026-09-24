#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_artigos_novos.py — Gera artigos HTML via OpenRouter para keywords aprovadas.

Uso:
  python gerar_artigos_novos.py --n 5        # testa com 5 artigos
  python gerar_artigos_novos.py              # processa todos aprovados
  python gerar_artigos_novos.py --dry        # lista sem criar
  python gerar_artigos_novos.py --skip-ai    # gera com conteúdo placeholder (sem IA)
  python gerar_artigos_novos.py --force      # sobrescreve artigos existentes
  python gerar_artigos_novos.py --cat Games  # filtra por categoria

Requer: OPENROUTER_API_KEY em .env (ou env var)
Depois de criar, faz commit+push automático para Vercel.
"""

import json, re, sys, time, subprocess, argparse, urllib.request, urllib.parse, os
from pathlib import Path
from datetime import date

# Carrega .env do trends-scanner (chave OpenRouter compartilhada, nao duplicada aqui)
_env_path = Path(r"C:\projetos\trends-scanner\.env")
if _env_path.exists():
    for line in _env_path.read_text('utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

KW_JSON   = Path(__file__).parent / "A_keywords_para_artigo.json"
KW_AMAZON = Path(__file__).parent / "A_keywords_amazon.json"
ART_DIR   = Path(r"C:\projetos\official-amazon-reviews\articles")
INDEX_JSON = ART_DIR / "index.json"
SITE_URL  = "https://official-amazon-reviews.vercel.app"
TODAY     = date.today().isoformat()


# ── SERP: busca concorrentes Google ──────────────────────────────────────────

def _fetch(url: str, timeout: int = 8) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124",
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(150_000).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def buscar_concorrentes(kw: str, is_ebook: bool = False) -> list:
    sufixo = "kindle ebook complete guide" if is_ebook else "best review 2026"
    q = urllib.parse.quote(f"{kw} {sufixo}")
    html = _fetch(f"https://www.google.com/search?q={q}&hl=en&gl=US&num=8")
    if not html:
        return []
    urls = []
    bloqueados = ["google.", "youtube.", "reddit."]
    for m in re.finditer(r'href="/url\?q=(https?://[^&"]+)', html):
        u = urllib.parse.unquote(m.group(1))
        if not any(d in u for d in bloqueados) and u not in urls:
            urls.append(u)
            if len(urls) >= 3:
                break
    return urls


def extrair_estrutura(html: str) -> dict:
    clean = lambda s: re.sub(r"<[^>]+>", "", s).strip()
    title = clean((re.search(r"<title[^>]*>(.*?)</title>", html, re.I) or ["",""])[1])
    h2s   = [clean(m.group(1)) for m in re.finditer(r"<h2[^>]*>(.*?)</h2>", html, re.I)]
    h3s   = [clean(m.group(1)) for m in re.finditer(r"<h3[^>]*>(.*?)</h3>", html, re.I)]
    texto = re.sub(r"\s{2,}", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.I))).strip()[:3000]
    return {
        "title": title,
        "h2s": [h for h in h2s[:8] if 3 < len(h) < 120],
        "h3s": [h for h in h3s[:8] if 3 < len(h) < 120],
        "palavras": len(html.split()),
        "texto": texto,
    }


def montar_contexto(analises: list) -> str:
    if not analises:
        return "No competitor data available."
    ctx = "TOP COMPETITORS RANKING ON GOOGLE:\n\n"
    for i, a in enumerate(analises, 1):
        ctx += f"[Competitor {i}] {a['url']}\n"
        ctx += f"- Title: {a['title']}\n"
        ctx += f"- H2s: {' | '.join(a['h2s'])}\n"
        ctx += f"- H3s: {' | '.join(a['h3s'][:5])}\n"
        ctx += f"- Word count: ~{a['palavras']}\n"
        ctx += f"- Content excerpt: {a['texto'][:600]}\n\n"
    return ctx


# ── Claude Haiku: gera buying guide + FAQ ────────────────────────────────────

def montar_prompt_ebook(keyword: str, contexto: str) -> str:
    return f"""You are an expert in informational SEO and digital product copywriting for Amazon KDP ebooks.

TARGET KEYWORD: "{keyword}"
LANGUAGE: American English (EN-US)

{contexto}

YOUR MISSION:
Generate HTML content for two sections of an article targeting readers who want to LEARN about "{keyword}":

1. COMPLETE GUIDE — section "how-choose-text" (inside <div class="how-choose-text">)
   - 6 to 8 subtopics with <h3> specific to "{keyword}"
   - Frame content around the READER'S PROBLEM, not a product to buy
   - Each H3 followed by <p> with 80-120 words addressing real reader pain points
   - Use emotional vocabulary: frustrated, overwhelmed, simple, step-by-step, easy, beginner-friendly
   - Structure per subtopic: problem → insight → actionable tip
   - Mention "{keyword}" naturally in 2-3 H3s or paragraphs
   - Last H3 MUST be "Get the Complete {keyword} Guide on Kindle" with a <p> explaining the ebook covers everything above in one place, available on Amazon Kindle
   - TOTAL: 600-900 words

2. FAQ — 8 questions a BEGINNER reader would ask about "{keyword}"
   - Topic questions (how to, what is, why, when, best way to) — NOT product or purchase questions
   - Each answer: minimum 4 sentences with actionable advice
   - Use "{keyword}" in the first 3 questions
   - AEO: self-sufficient answers (AI can cite without context)
   - Tone: helpful teacher, not salesperson
   - TOTAL: 400-600 words

RULES:
- Return ONLY the JSON below. Zero markdown. Zero explanation.
- Keyword "{keyword}" must appear EXACTLY as written (no spelling corrections)
- Content in American English
- Do NOT copy competitor text — generate ORIGINAL and SUPERIOR content

RETURN EXACTLY THIS JSON:
{{
  "buying_guide_html": "<h3>...</h3><p>...</p><h3>...</h3><p>...</p>...",
  "faq": [
    {{"q": "question 1?", "a": "complete answer with actionable advice..."}},
    {{"q": "question 2?", "a": "..."}},
    {{"q": "question 3?", "a": "..."}},
    {{"q": "question 4?", "a": "..."}},
    {{"q": "question 5?", "a": "..."}},
    {{"q": "question 6?", "a": "..."}},
    {{"q": "question 7?", "a": "..."}},
    {{"q": "question 8?", "a": "..."}}
  ]
}}"""


def montar_prompt_produto(keyword: str, contexto: str) -> str:
    return f"""You are an expert product reviewer and SEO copywriter for Amazon affiliate sites.

TARGET KEYWORD: "{keyword}"
LANGUAGE: American English (EN-US)

{contexto}

YOUR MISSION:
Generate HTML content for two sections of an Amazon affiliate article targeting buyers searching "{keyword}":

1. BUYING GUIDE — section "how-choose-text" (inside <div class="how-choose-text">)
   - 6 to 8 subtopics with <h3> specific to "{keyword}"
   - Frame content around the BUYER'S DECISION: features, specs, comparisons, use cases
   - Each H3 followed by <p> with 80-120 words with practical buying advice
   - Use buyer vocabulary: best, top-rated, worth buying, value for money, pros/cons
   - Structure per subtopic: what to look for → why it matters → buying tip
   - Mention "{keyword}" naturally in 2-3 H3s or paragraphs
   - Last H3 MUST be "Best {keyword} on Amazon 2026" with a <p> recommending to check Amazon for current best sellers and deals
   - TOTAL: 600-900 words

2. FAQ — 8 questions a buyer would ask before purchasing "{keyword}"
   - Questions about features, quality, price, compatibility, alternatives
   - Each answer: minimum 4 sentences with practical advice
   - Use "{keyword}" in the first 3 questions
   - AEO: self-sufficient answers (AI can cite without context)
   - Tone: trusted expert reviewer
   - TOTAL: 400-600 words

RULES:
- Return ONLY the JSON below. Zero markdown. Zero explanation.
- Keyword "{keyword}" must appear EXACTLY as written
- Content in American English
- Do NOT copy competitor text — generate ORIGINAL and SUPERIOR content

RETURN EXACTLY THIS JSON:
{{
  "buying_guide_html": "<h3>...</h3><p>...</p><h3>...</h3><p>...</p>...",
  "faq": [
    {{"q": "question 1?", "a": "complete answer with actionable advice..."}},
    {{"q": "question 2?", "a": "..."}},
    {{"q": "question 3?", "a": "..."}},
    {{"q": "question 4?", "a": "..."}},
    {{"q": "question 5?", "a": "..."}},
    {{"q": "question 6?", "a": "..."}},
    {{"q": "question 7?", "a": "..."}},
    {{"q": "question 8?", "a": "..."}}
  ]
}}"""


# Ordem testada em 22/09: nex-agi retorna JSON limpo; nemotron mistura
# "raciocinio" dentro do content (quebra o parser); os gemma:free estao
# com 429 constante no pool gratuito. Prioriza o que funciona.
# Ampliado em 22/09 noite (retestes mostraram nex-agi/nemotron/gemma falhando
# de forma consistente, nao so passageira) - mais opcoes gratuitas no fallback.
FREE_MODELS = [
    "nex-agi/nex-n2.5-pro:free",
    "nex-agi/nex-n2.5-mini:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "deepseek/deepseek-chat-v3.1:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


def gerar_com_ia(client, keyword: str, contexto: str, is_ebook: bool) -> dict:
    prompt = montar_prompt_ebook(keyword, contexto) if is_ebook else montar_prompt_produto(keyword, contexto)
    modelos = FREE_MODELS
    last_err = None
    for model in modelos:
        for tentativa in range(2):
            try:
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=4000,
                    messages=[{"role": "user", "content": prompt}],
                )
                if not response.choices:
                    raise ValueError(f"Sem choices na resposta ({model})")
                raw = (response.choices[0].message.content or "").strip()
                if not raw:
                    raise ValueError(f"Content vazio ({model})")
                match = re.search(r"\{[\s\S]*\}", raw)
                if not match:
                    raise ValueError(f"Response is not valid JSON ({model})")
                return json.loads(match.group(0))
            except Exception as e:
                last_err = e
                print(f"    [modelo {model} falhou: {e}]")
                if "429" in str(e) and tentativa == 0:
                    time.sleep(12)
                    continue
                break
    raise last_err

# ── HTML Template ────────────────────────────────────────────────────────────

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f4f6f9;color:#222;font-size:16px}
.urgency-bar{background:#cc0000;color:#fff;text-align:center;padding:8px;font-size:.85rem;font-weight:700;letter-spacing:.5px;position:sticky;top:0;z-index:200}
header{background:#fff;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.08);position:sticky;top:36px;z-index:100}
.logo{font-size:1rem;font-weight:700;color:#ff9900;display:flex;align-items:center;gap:6px}
.btn-header{background:#ff9900;color:#fff;border:none;padding:8px 18px;border-radius:6px;font-weight:700;cursor:pointer;font-size:.85rem;text-decoration:none}
.hero{background:#fff;display:grid;grid-template-columns:280px 1fr;gap:32px;max-width:1100px;margin:24px auto;padding:32px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,.07)}
@media(max-width:768px){.hero{grid-template-columns:1fr}}
.hero-img{width:100%;border-radius:8px;object-fit:cover;max-height:380px}
.hero-badge{display:inline-block;background:#cc0000;color:#fff;padding:4px 10px;border-radius:4px;font-size:.78rem;font-weight:700;margin-bottom:12px}
.hero-title{font-size:1.6rem;font-weight:800;line-height:1.3;margin-bottom:12px}
.hero-desc{font-size:.93rem;color:#555;margin-bottom:20px;line-height:1.6}
.hero-rating{display:flex;align-items:center;gap:8px;margin-bottom:16px}
.stars{color:#ff9900;font-size:1.1rem}
.rating-text{font-size:.85rem;color:#666}
.btn-main{display:block;background:linear-gradient(135deg,#ff6600,#cc0000);color:#fff;text-align:center;padding:16px;border-radius:10px;font-size:1.05rem;font-weight:800;text-decoration:none;margin-bottom:10px;box-shadow:0 4px 12px rgba(204,0,0,.3)}
.btn-main:hover{opacity:.92}
.trust-row{display:flex;gap:16px;font-size:.78rem;color:#666;justify-content:center;flex-wrap:wrap}
.article-wrap{max-width:1000px;margin:0 auto;padding:0 20px 60px}
.article-title{font-size:1.8rem;font-weight:800;text-align:center;margin:30px 0 10px;line-height:1.3}
.article-subtitle{text-align:center;color:#555;font-size:.95rem;margin-bottom:20px}
.breadcrumb{font-size:.8rem;color:#888;margin-bottom:16px}
.breadcrumb a{color:#0066c0;text-decoration:none}
.affiliate-note{background:#fff8e1;border-left:4px solid #ffc107;padding:12px 16px;border-radius:6px;font-size:.82rem;color:#555;margin-bottom:24px}
.toc{background:#fff;border-radius:10px;padding:20px;margin-bottom:24px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.toc-title{font-weight:700;margin-bottom:12px;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.toc ul{list-style:none;padding-left:8px}
.toc ul li{margin-bottom:8px}
.toc ul li a{color:#0066c0;font-size:.88rem;text-decoration:none}
.toc ul li a:hover{text-decoration:underline}
.article-section{margin-bottom:36px}
.article-section h2{font-size:1.3rem;font-weight:800;margin-bottom:14px;padding-bottom:8px;border-bottom:2px solid #f0f0f0}
.article-section p{line-height:1.7;color:#333;margin-bottom:12px;font-size:.95rem}
.how-choose-text{background:#fff;border-radius:10px;padding:24px;box-shadow:0 2px 8px rgba(0,0,0,.06);line-height:1.7;font-size:.95rem;color:#333}
.how-choose-text h3{font-size:1.05rem;font-weight:700;margin:16px 0 8px}
.how-choose-text p{margin-bottom:12px}
.how-choose-text ul{padding-left:20px;margin-bottom:12px}
.how-choose-text ul li{margin-bottom:6px}
.cta-box{background:linear-gradient(135deg,#fff8e1,#fff3cd);border:2px solid #ff9900;border-radius:12px;padding:28px;text-align:center;margin:32px 0}
.cta-box h3{font-size:1.2rem;font-weight:800;margin-bottom:8px}
.cta-box p{color:#555;margin-bottom:16px;font-size:.9rem}
.faq-section{margin-bottom:36px}
.faq-section h2{font-size:1.3rem;font-weight:800;margin-bottom:16px;text-align:center}
.faq-item{background:#fff;border-radius:8px;margin-bottom:10px;box-shadow:0 1px 6px rgba(0,0,0,.06);overflow:hidden}
.faq-q{padding:14px 18px;font-weight:700;font-size:.9rem;cursor:pointer;display:flex;justify-content:space-between;align-items:center}
.faq-q:hover{background:#fff8e1}
.faq-a{display:none;padding:0 18px 14px;font-size:.88rem;color:#444;line-height:1.6}
.faq-item.open .faq-a{display:block}
.faq-item.open .faq-q{color:#ff9900}
.site-footer{background:#222;color:#aaa;text-align:center;padding:30px 20px;font-size:.82rem}
.footer-badges{display:flex;justify-content:center;gap:20px;margin-bottom:12px;flex-wrap:wrap}
.footer-badges span{background:#333;padding:6px 14px;border-radius:20px;font-size:.78rem}
.footer-btn{display:inline-block;margin-top:14px;background:#ff9900;color:#fff;padding:10px 24px;border-radius:6px;font-weight:700;text-decoration:none;font-size:.9rem}
"""

def make_html(slug, kw, top_kw, nome, link_afiliado, volume, kd, ai_dados=None):
    """
    ai_dados: dict com 'buying_guide_html' e 'faq' gerados pelo Claude.
              Se None, usa conteúdo placeholder estático.
    """
    asin = link_afiliado.split('/dp/')[-1].split('?')[0] if '/dp/' in link_afiliado else ''
    img_url = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg" if asin else ""

    kw_title = top_kw.title()
    kw_lower = top_kw.lower()
    canon    = f"{SITE_URL}/articles/{slug}/"
    desc     = f"Looking for {kw_title}? Our complete 2026 guide covers everything you need to know. Expert analysis, reader reviews, and the best place to buy {kw_lower}."

    # FAQ: usa Claude se disponível, senão placeholder
    if ai_dados and ai_dados.get("faq"):
        faq_mainEntity = [
            {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
            for item in ai_dados["faq"]
        ]
        faq_items_html = ""
        for item in ai_dados["faq"]:
            q = item["q"].replace('"', "&quot;")
            faq_items_html += f"""
    <div class="faq-item">
      <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">{q} <span>▾</span></div>
      <div class="faq-a">{item['a']}</div>
    </div>"""
    else:
        faq_mainEntity = [
            {"@type": "Question", "name": f"Which {kw_lower} is best overall?", "acceptedAnswer": {"@type": "Answer", "text": f"Based on our research and reader reviews, {nome} stands out as the top choice for {kw_lower} in 2026 — offering excellent value and quality."}},
            {"@type": "Question", "name": f"Is {kw_title} available on Amazon?", "acceptedAnswer": {"@type": "Answer", "text": f"Yes! {kw_title} is available on Amazon with fast shipping for Prime members. Click the button above to check current availability and price."}},
            {"@type": "Question", "name": f"What makes {kw_title} worth reading?", "acceptedAnswer": {"@type": "Answer", "text": f"{kw_title} delivers practical insights and in-depth coverage on the topic. Thousands of readers have rated it highly for clarity and usefulness."}},
            {"@type": "Question", "name": "Can I get this as a Kindle eBook?", "acceptedAnswer": {"@type": "Answer", "text": "Many titles are available in Kindle format for instant download. Check the Amazon product page for eBook and audiobook options."}},
            {"@type": "Question", "name": "Is there a money-back guarantee?", "acceptedAnswer": {"@type": "Answer", "text": "Amazon offers a 30-day return policy for physical books. Kindle purchases may be eligible for a refund within 7 days if you haven't read more than 10% of the book."}}
        ]
        faq_items_html = ""
        for q_obj in faq_mainEntity:
            faq_items_html += f"""
    <div class="faq-item">
      <div class="faq-q" onclick="this.parentElement.classList.toggle('open')">{q_obj['name']} <span>▾</span></div>
      <div class="faq-a">{q_obj['acceptedAnswer']['text']}</div>
    </div>"""

    # Buying guide: usa Claude se disponível, senão placeholder
    if ai_dados and ai_dados.get("buying_guide_html"):
        how_choose_content = ai_dados["buying_guide_html"]
    else:
        how_choose_content = f"""<p>When looking for the best <strong>{kw_lower}</strong>, there are several key factors to consider. This guide breaks down everything that matters so you can make an informed decision.</p>
      <h3>Key Things to Look For</h3>
      <ul>
        <li><strong>Content Quality:</strong> Look for titles with well-researched, up-to-date information and clear writing.</li>
        <li><strong>Author Credentials:</strong> Choose books written by recognized experts in the field.</li>
        <li><strong>Reader Reviews:</strong> Check Amazon ratings and comments from verified buyers.</li>
        <li><strong>Format Options:</strong> Consider whether a Kindle edition, paperback, or hardcover suits your needs best.</li>
        <li><strong>Price vs. Value:</strong> The most expensive option isn't always the best — compare what you get for your money.</li>
      </ul>
      <h3>Our Recommendation for 2026</h3>
      <p>After thorough research, <strong>{nome}</strong> stands out as the top choice for anyone interested in <em>{kw_lower}</em>. It delivers excellent value, practical insights, and has earned consistently positive feedback from thousands of readers.</p>
      <h3>Who Should Read This?</h3>
      <p>This title is ideal for anyone who wants to gain a deep understanding of <em>{kw_lower}</em>, whether you're a complete beginner or looking to expand your existing knowledge.</p>"""

    # JSON-LD
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Article",
                "headline": f"{kw_title} - Complete Guide & Review 2026",
                "about": {"@type": "Thing", "name": kw_title},
                "datePublished": TODAY,
                "dateModified": TODAY,
                "publisher": {"@type": "Organization", "name": "Official Amazon Reviews"}
            },
            {
                "@type": "BreadcrumbList",
                "name": f"{kw_title} Review",
                "itemListElement": [
                    {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE_URL + "/"},
                    {"@type": "ListItem", "position": 2, "name": "Books", "item": SITE_URL + "/articles/"},
                    {"@type": "ListItem", "position": 3, "name": kw_title, "item": canon}
                ]
            },
            {
                "@type": "FAQPage",
                "@id": canon + "#faq",
                "mainEntity": faq_mainEntity
            }
        ]
    }

    img_tag = f'<img src="{img_url}" alt="{kw_title}" class="hero-img" loading="lazy">' if img_url else f'<div class="hero-img" style="background:#f0e6d3;display:flex;align-items:center;justify-content:center;font-size:3rem;">📚</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{kw_title} - Complete Guide &amp; Review 2026</title>
  <meta name="description" content="{desc}">
  <meta property="og:title" content="{kw_title} - Complete Guide &amp; Review 2026">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="article">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{kw_title} - Complete Guide &amp; Review 2026">
  <link rel="canonical" href="{canon}">
  <script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
  <style>{CSS}</style>
</head>
<body>

<div class="urgency-bar">📚 BEST PRICE: Get <strong>{kw_title}</strong> on Amazon → <a href="{link_afiliado}" style="color:#fff;text-decoration:underline" rel="nofollow" target="_blank">Check Now</a></div>

<header>
  <div class="logo">⭐ Official Amazon Reviews</div>
  <a href="{link_afiliado}" class="btn-header" rel="nofollow" target="_blank">Buy on Amazon →</a>
</header>

<!-- HERO -->
<div class="hero">
  {img_tag}
  <div class="hero-content">
    <span class="hero-badge">#1 RECOMMENDED 2026</span>
    <h1 class="hero-title">{nome}</h1>
    <p class="hero-desc">{desc}</p>
    <div class="hero-rating">
      <span class="stars">★★★★★</span>
      <span class="rating-text">Highly rated · Amazon Best Seller</span>
    </div>
    <a href="{link_afiliado}" class="btn-main" rel="nofollow" target="_blank">
      🛒 Check Price &amp; Availability on Amazon
    </a>
    <div class="trust-row">
      <span>✓ Fast Shipping</span>
      <span>✓ Amazon Protection</span>
      <span>✓ Easy Returns</span>
    </div>
  </div>
</div>

<!-- ARTICLE -->
<div class="article-wrap">

  <h2 class="article-title">{kw_title} - Complete Guide &amp; Review 2026</h2>
  <p class="article-subtitle">Everything you need to know before you buy</p>

  <div class="breadcrumb">
    <a href="{SITE_URL}/">Home</a> &rsaquo; <a href="{SITE_URL}/articles/">Books &amp; Reviews</a> &rsaquo; {kw_title}
  </div>

  <div class="affiliate-note">
    ⚠️ <strong>Affiliate Disclosure:</strong> This page contains Amazon affiliate links. We may earn a small commission at no extra cost to you if you purchase through our links. This helps us maintain this resource.
  </div>

  <!-- TOC -->
  <div class="toc">
    <div class="toc-title" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">
      📋 Table of Contents <span>▾</span>
    </div>
    <ul>
      <li><a href="#section-1">What Is {kw_title}?</a></li>
      <li><a href="#section-2">{kw_title} Complete Guide 2026</a></li>
      <li><a href="#section-3">Why Buy on Amazon</a></li>
      <li><a href="#section-9">Frequently Asked Questions</a></li>
    </ul>
  </div>

  <!-- SECTION 1 -->
  <div class="article-section" id="section-1">
    <h2>What Is {kw_title}?</h2>
    <p><strong>{kw_title}</strong> is one of the most searched topics in its category, with over {volume:,} monthly searches. Whether you're a beginner or an experienced reader, understanding what makes a great <em>{kw_lower}</em> can save you time and money.</p>
    <p>{nome} is a standout option that consistently receives high praise from readers worldwide. It combines depth of content with accessibility, making it suitable for a wide range of audiences.</p>
    <p>In this complete guide, we'll cover everything you need to know about <strong>{kw_lower}</strong> — from what to look for, to where to find the best deal on Amazon.</p>
  </div>

  <!-- SECTION 2 — how-choose-text -->
  <div class="article-section" id="section-2">
    <h2>{kw_title} Complete Guide 2026</h2>
    <div class="how-choose-text">
      {how_choose_content}
    </div>
  </div>

  <!-- CTA BOX -->
  <div class="cta-box">
    <h3>Ready to Get {kw_title}?</h3>
    <p>Available on Amazon with fast shipping. Check current price and availability now.</p>
    <a href="{link_afiliado}" class="btn-main" rel="nofollow" target="_blank" style="max-width:400px;margin:0 auto">
      🛒 View on Amazon — Check Price
    </a>
  </div>

  <!-- SECTION 3 -->
  <div class="article-section" id="section-3">
    <h2>Why Buy {kw_title} on Amazon</h2>
    <p>Amazon is the best place to buy <strong>{kw_lower}</strong> for several reasons:</p>
    <ul style="padding-left:20px;line-height:2">
      <li>✓ <strong>Prime Shipping:</strong> Get your order in 1-2 days with Prime membership</li>
      <li>✓ <strong>Easy Returns:</strong> 30-day hassle-free return policy on most books</li>
      <li>✓ <strong>Kindle Option:</strong> Many titles available for instant digital download</li>
      <li>✓ <strong>Verified Reviews:</strong> Thousands of authentic reader reviews to guide your choice</li>
      <li>✓ <strong>Best Price:</strong> Amazon consistently offers competitive pricing</li>
    </ul>
  </div>

  <!-- FAQ -->
  <div class="faq-section" id="section-9">
    <h2>Frequently Asked Questions (FAQ)</h2>
    {faq_items_html}
  </div>

</div>

<footer class="site-footer">
  <div class="footer-badges">
    <span>✓ Amazon Verified</span>
    <span>✓ Expert Reviewed</span>
    <span>✓ Updated 2026</span>
  </div>
  <p>© 2026 Official Amazon Reviews. We are a participant in the Amazon Services LLC Associates Program.</p>
  <a href="{SITE_URL}" class="footer-btn">← Back to Home</a>
</footer>

<script>
// FAQ toggle
document.querySelectorAll('.faq-q').forEach(q => {{
  q.addEventListener('click', () => q.parentElement.classList.toggle('open'));
}});
// Open first FAQ
const first = document.querySelector('.faq-item');
if (first) first.classList.add('open');
</script>

</body>
</html>"""
    return html


EBOOK_CATS = {'livros', 'kindle e ebooks'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n',         type=int, default=0,  help='Limite de artigos a criar')
    ap.add_argument('--dry',       action='store_true',  help='Só lista, não cria')
    ap.add_argument('--force',     action='store_true',  help='Sobrescreve artigos existentes')
    ap.add_argument('--skip-ai',   action='store_true',  help='Gera com placeholder (sem IA)')
    ap.add_argument('--skip-serp', action='store_true',  help='Não busca concorrentes Google')
    ap.add_argument('--cat',       type=str, default='', help='Filtrar por categoria (parcial)')
    ap.add_argument('--vol',       type=int, default=500, help='Volume mínimo (padrão 500)')
    ap.add_argument('--kd',        type=int, default=50,  help='KD máximo (padrão 50)')
    args = ap.parse_args()

    # OpenRouter client
    client = None
    if not args.skip_ai and not args.dry:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            print("ERRO: OPENROUTER_API_KEY não definida no .env. Use --skip-ai para gerar sem IA.")
            sys.exit(1)
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                timeout=20.0,
                max_retries=0,
            )
        except ImportError:
            print("ERRO: openai package não instalado. Execute: pip install openai")
            sys.exit(1)

    data = json.loads(KW_JSON.read_text('utf-8'))

    def aprovado(v):
        vol = int(v.get('volume', 0) or 0)
        kd  = v.get('kd') if v.get('kd') is not None else 999
        fonte = v.get('fonte', '')
        return (vol >= args.vol and kd < args.kd and fonte == 'semrush')

    candidatos = [(k, v) for k, v in data.items() if aprovado(v)]
    if args.cat:
        candidatos = [(k, v) for k, v in candidatos if args.cat.lower() in v.get('categoria', '').lower()]
    candidatos.sort(key=lambda x: int(x[1].get('volume', 0) or 0), reverse=True)

    # Índice existente
    idx_raw = INDEX_JSON.read_text('utf-8') if INDEX_JSON.exists() else '[]'
    idx = json.loads(idx_raw)
    slugs_existentes = {e['slug'] for e in idx}

    kw_amazon = json.loads(KW_AMAZON.read_text('utf-8')) if KW_AMAZON.exists() else {}

    if args.force:
        pendentes = candidatos
    else:
        pendentes = [(k, v) for k, v in candidatos if k not in slugs_existentes and not (ART_DIR / k).exists()]

    total_cat = {}
    for _, v in pendentes:
        c = v.get('categoria', 'Outros')
        total_cat[c] = total_cat.get(c, 0) + 1

    print(f"Aprovados: {len(candidatos)} | Existentes: {len(candidatos)-len(pendentes)} | Pendentes: {len(pendentes)}")
    if total_cat:
        print("Por categoria: " + " | ".join(f"{c}={n}" for c, n in sorted(total_cat.items(), key=lambda x: -x[1])[:8]))

    if args.dry:
        for k, v in pendentes[:30]:
            print(f"  {k[:65]:<65} {v.get('categoria','?'):<25} vol={v.get('volume',0):>8,} kd={v.get('kd','?'):>3}")
        return

    if args.n:
        pendentes = pendentes[:args.n]

    criados = 0
    for i, (key, v) in enumerate(pendentes, 1):
        top_kw_raw = v.get('top_kw') or ''
        top_kw = top_kw_raw if len(top_kw_raw.split()) >= 2 else (v.get('keyword') or top_kw_raw or key)
        nome      = v.get('nome', top_kw)
        link      = v.get('link_afiliado', '')
        vol       = int(v.get('volume', 0) or 0)
        kd        = v.get('kd', 0)
        slug      = key
        cat_lower = v.get('categoria', '').lower()
        is_ebook  = cat_lower in EBOOK_CATS

        print(f"\n[{i}/{len(pendentes)}] {top_kw} | {v.get('categoria','')} (vol={vol:,}, kd={kd})")

        ai_dados = None
        if client:
            try:
                contexto = "No competitor data available."
                if not args.skip_serp:
                    print(f"  Buscando concorrentes...")
                    urls = buscar_concorrentes(top_kw, is_ebook=is_ebook)
                    analises = []
                    for url in urls:
                        html_c = _fetch(url, timeout=7)
                        if html_c and len(html_c) > 1000:
                            s = extrair_estrutura(html_c)
                            s["url"] = url
                            analises.append(s)
                            print(f"     OK {url[:55]}")
                    contexto = montar_contexto(analises)

                tipo_str = "ebook" if is_ebook else "produto"
                print(f"  Gerando conteudo ({tipo_str}) via OpenRouter...")
                ai_dados = gerar_com_ia(client, top_kw, contexto, is_ebook)
                print(f"  OK {len(ai_dados.get('faq', []))} FAQs geradas")
            except Exception as e:
                print(f"  AVISO: IA falhou ({e}), usando placeholder")
                ai_dados = None

        # Gera HTML
        art_path = ART_DIR / slug
        art_path.mkdir(parents=True, exist_ok=True)
        html = make_html(slug, v.get('keyword', top_kw), top_kw, nome, link, vol, kd, ai_dados)
        (art_path / 'index.html').write_text(html, encoding='utf-8')

        # Atualiza index.json
        asin = link.split('/dp/')[-1].split('?')[0] if '/dp/' in link else ''
        img  = f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg" if asin else ""
        if slug not in slugs_existentes:
            idx.append({
                "slug": slug,
                "title": f"{top_kw.title()} - Complete Guide & Review 2026",
                "description": f"Looking for {top_kw.lower()}? Our complete 2026 guide covers everything.",
                "image": img,
                "category": v.get('categoria', 'Books'),
                "date": TODAY
            })
            slugs_existentes.add(slug)

        # Atualiza keywords_amazon.json
        cat_kw = "ebook" if is_ebook else v.get('categoria', 'produto')
        kw_amazon[slug] = {"nome": nome, "top_kw": top_kw, "volume": vol, "kd": kd, "categoria": cat_kw, "link_afiliado": link}

        criados += 1

        if i < len(pendentes):
            time.sleep(5)

        # Commit parcial a cada 20 artigos para não perder progresso
        if criados % 20 == 0:
            INDEX_JSON.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')
            KW_AMAZON.write_text(json.dumps(kw_amazon, ensure_ascii=False, indent=2), encoding='utf-8')
            repo = r"C:\projetos\official-amazon-reviews"
            try:
                subprocess.run(['git', '-C', repo, 'add', '-A'], check=True, capture_output=True)
                subprocess.run(['git', '-C', repo, 'commit', '-m', f"SEO: batch +{criados} articles (auto) [{TODAY}]"], check=True, capture_output=True)
                subprocess.run(['git', '-C', repo, 'push'], check=True, capture_output=True)
                print(f"\n  [batch commit] {criados} artigos publicados no Vercel")
            except Exception:
                pass

    if criados == 0:
        print("Nenhum artigo novo para criar.")
        return

    # Salva índices finais
    INDEX_JSON.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding='utf-8')
    KW_AMAZON.write_text(json.dumps(kw_amazon, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nindex.json: {len(idx)} artigos | keywords_amazon.json: {len(kw_amazon)} keywords")

    # Commit final
    repo = r"C:\projetos\official-amazon-reviews"
    print("\nCommitando e publicando no Vercel...")
    try:
        subprocess.run(['git', '-C', repo, 'add', '-A'], check=True)
        msg = f"SEO: add {criados} new articles [{TODAY}]"
        subprocess.run(['git', '-C', repo, 'commit', '-m', msg], check=True)
        subprocess.run(['git', '-C', repo, 'push'], check=True)
        print(f"\nOK {criados} artigos criados e publicados no Vercel!")
    except subprocess.CalledProcessError as e:
        print(f"AVISO Git: {e}")
        print(f"Arquivos criados localmente em {ART_DIR}")

    print(f"\nProximo passo: node melhorar_com_serp.js  (otimizacao HYPEN SEO)")


if __name__ == '__main__':
    main()
