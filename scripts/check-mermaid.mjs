// Extrae cada bloque ```mermaid de docs/ y lo renderiza con mermaid-cli para detectar errores de sintaxis.
import { readFileSync, readdirSync, writeFileSync, mkdtempSync, statSync, existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const out = mkdtempSync(join(tmpdir(), 'mermaid-'));
// Usa un navegador ya instalado si existe (evita descargar Chromium): CHROME_PATH o rutas comunes.
const navegador = [process.env.CHROME_PATH,
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find((x) => x && existsSync(x));
const extra = [];
if (navegador) {
  const cfg = join(out, 'puppeteer.json');
  writeFileSync(cfg, JSON.stringify({ executablePath: navegador, args: ['--no-sandbox'] }));
  extra.push('-p', `"${cfg}"`);
}
const files = [];
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    const full = join(dir, f);
    if (statSync(full).isDirectory()) walk(full);
    else if (f.endsWith('.md')) files.push(full);
  }
};
walk(join(root, 'docs'));

let total = 0;
const fallos = [];
for (const file of files) {
  const blocks = [...readFileSync(file, 'utf8').matchAll(/```mermaid\r?\n([\s\S]*?)```/g)];
  blocks.forEach((m, i) => {
    total++;
    const src = join(out, `${total}.mmd`);
    writeFileSync(src, m[1]);
    try {
      execFileSync('npx', ['--yes', '@mermaid-js/mermaid-cli@11.4.2', '-i', `"${src}"`, '-o', `"${join(out, `${total}.svg`)}"`, '-q', ...extra], { stdio: 'pipe', shell: true });
    } catch (e) {
      fallos.push(`${file.replace(root, '')} bloque ${i + 1}: ${String(e.stderr || e.message).split('\n').slice(0, 4).join(' ')}`);
    }
  });
}
for (const f of fallos) console.error(`✗ ${f}`);
console.log(`${total - fallos.length}/${total} diagramas Mermaid renderizan correctamente.`);
process.exit(fallos.length ? 1 : 0);
