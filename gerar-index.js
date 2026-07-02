// Gera articles/index.json a partir dos artigos existentes
const fs = require('fs');
const path = require('path');

const ARTICLES_DIR = path.join(__dirname, 'articles');
const OUTPUT = path.join(ARTICLES_DIR, 'index.json');

function extract(html, regex, group = 1) {
  const m = html.match(regex);
  return m ? m[group].replace(/&amp;/g, '&').replace(/&#39;/g, "'").replace(/&quot;/g, '"').trim() : '';
}

function buildIndex(articlesDir) {
  const folders = fs.readdirSync(articlesDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);

  const articles = [];

  for (const slug of folders) {
    const htmlPath = path.join(articlesDir, slug, 'index.html');
    if (!fs.existsSync(htmlPath)) continue;

    const html = fs.readFileSync(htmlPath, 'utf8');

    const title = extract(html, /property="og:title"\s+content="([^"]+)"/);
    const description = extract(html, /property="og:description"\s+content="([^"]+)"/);
    const image = extract(html, /property="og:image"\s+content="([^"]+)"/);
    const date = extract(html, /name="citation_publication_date"\s+content="([^"]+)"/);

    // Extrai categoria do schema "about"
    const aboutMatch = html.match(/"about":\s*\[{"@type":"Thing","name":"([^"]+)"}/);
    const category = aboutMatch ? aboutMatch[1] : 'General';

    if (!title) continue;

    articles.push({ slug, title, description, image, category, date });
  }

  // Ordena por data decrescente
  articles.sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));

  fs.writeFileSync(OUTPUT, JSON.stringify(articles, null, 2), 'utf8');
  console.log(`✅ index.json gerado com ${articles.length} artigos em ${OUTPUT}`);
}

buildIndex(ARTICLES_DIR);
