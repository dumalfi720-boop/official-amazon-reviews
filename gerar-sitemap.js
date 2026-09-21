const fs = require('fs');
const path = require('path');

const SITE = 'https://official-amazon-reviews.vercel.app';
const articles = require('./articles/index.json');

const today = new Date().toISOString().split('T')[0];

const urls = [
  { loc: `${SITE}/`, lastmod: today, changefreq: 'daily', priority: '1.0' },
  ...articles.map(a => ({
    loc: `${SITE}/articles/${a.slug}/`,
    lastmod: a.date || today,
    changefreq: 'weekly',
    priority: '0.8',
  })),
];

const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls
  .map(
    u => `  <url>\n    <loc>${u.loc}</loc>\n    <lastmod>${u.lastmod}</lastmod>\n    <changefreq>${u.changefreq}</changefreq>\n    <priority>${u.priority}</priority>\n  </url>`
  )
  .join('\n')}\n</urlset>\n`;

fs.writeFileSync(path.join(__dirname, 'sitemap.xml'), xml, 'utf-8');
console.log(`sitemap.xml gerado com ${urls.length} URLs (${articles.length} artigos + home)`);
