// Remove countdown timer de todos os artigos existentes
const fs = require('fs');
const path = require('path');

const ARTICLES_DIR = path.join(__dirname, 'articles');

const folders = fs.readdirSync(ARTICLES_DIR, { withFileTypes: true })
  .filter(d => d.isDirectory())
  .map(d => d.name);

let editados = 0;
let sem_countdown = 0;

for (const slug of folders) {
  const htmlPath = path.join(ARTICLES_DIR, slug, 'index.html');
  if (!fs.existsSync(htmlPath)) continue;

  let html = fs.readFileSync(htmlPath, 'utf8');
  const original = html;

  // Remove div.timer-box (inclui o span de texto e o span.countdown dentro)
  html = html.replace(/<div class="timer-box">[\s\S]*?<\/div>/g, '');

  // Remove CSS .timer-box e .countdown (cada um em sua própria linha)
  html = html.replace(/\s*\.timer-box\{[^}]+\}/g, '');
  html = html.replace(/\s*\.countdown\{[^}]+\}/g, '');

  // Remove bloco JS do countdown (comentário + forEach)
  html = html.replace(/\/\/ Countdown timers\s*document\.querySelectorAll\('\.countdown'\)\.forEach[\s\S]*?\}\);\s*/g, '');

  if (html !== original) {
    fs.writeFileSync(htmlPath, html, 'utf8');
    editados++;
  } else {
    sem_countdown++;
  }
}

console.log(`✅ Countdown removido de ${editados} artigos.`);
if (sem_countdown > 0) console.log(`ℹ️  ${sem_countdown} artigos já estavam sem countdown.`);
