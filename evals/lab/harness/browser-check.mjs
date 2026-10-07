// Browser half of the quality pass (RUBRIC block A). Copied into .tools/ and run there
// so it resolves playwright, axe and lighthouse from .tools/node_modules.
//   node browser-check.mjs <baseUrl> <outDir>
// Writes <outDir>/browser.json and screenshots under <outDir>/shots/.
import fs from 'node:fs';
import path from 'node:path';
import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import lighthouse from 'lighthouse';
import desktopConfig from 'lighthouse/core/config/desktop-config.js';
import * as chromeLauncher from 'chrome-launcher';

const [baseUrl, outDir] = process.argv.slice(2);
const shots = path.join(outDir, 'shots');
fs.mkdirSync(shots, { recursive: true });
const WIDTHS = [320, 768, 1280, 2560];
const MAX_ROUTES = 8;
const slug = (r) => (r === '/' ? 'home' : r.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, ''));

const result = { schemaVersion: 2, baseUrl, demoLoaded: false, demoVerification: "unverified", routes: [], expectedRoutes: [], requestedWidths: WIDTHS, widthProbes: {}, axeCompleted: [], consoleErrors: [], overflow: [], axe: {}, lighthouse: null };

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await context.newPage();
page.on('console', (m) => { if (m.type() === 'error') result.consoleErrors.push({ url: page.url(), text: m.text().slice(0, 300) }); });
page.on('pageerror', (e) => result.consoleErrors.push({ url: page.url(), text: `pageerror: ${String(e).slice(0, 300)}` }));

const settle = async () => {
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
};

try {
  const initialResponse = await page.goto(baseUrl, { timeout: 30000 });
  if (!initialResponse?.ok()) throw new Error(`Entry HTTP ${initialResponse?.status()}`);
  await settle();
  await page.screenshot({ path: path.join(shots, 'first-run.png'), fullPage: true });

  // Load the demo data the prompt asks for (F1), so the other screens have content.
  const demo = page.getByRole('button', { name: /dados de exemplo/i }).or(page.getByText(/carregar dados de exemplo/i)).first();
  if (await demo.count()) {
    await demo.click({ timeout: 5000 });
    result.demoClickCompleted = true;
    await page.waitForTimeout(4000);
    await settle();
    // A click is not evidence that demo data exists. A separate application-specific
    // behavior probe must establish F1; keep this field unverified here.
  }

  const hrefs = await page.$$eval('a[href^="/"]', (as) => as.map((a) => a.getAttribute('href')));
  const routes = ['/', ...new Set(hrefs.map((h) => h.split(/[?#]/)[0]).filter((h) => h && h !== '/'))].slice(0, MAX_ROUTES);

  result.expectedRoutes = routes;
  for (const route of routes) {
    const entry = { route, ok: false };
    result.widthProbes[route] = [];
    try {
      await page.setViewportSize({ width: 1280, height: 800 });
      const response = await page.goto(new URL(route, baseUrl).toString(), { timeout: 30000 });
      entry.status = response?.status();
      if (!response?.ok()) throw new Error(`Route HTTP ${entry.status}`);
      await settle();
      await page.screenshot({ path: path.join(shots, `${slug(route)}-1280.png`), fullPage: true });

      const axe = await new AxeBuilder({ page }).analyze();
      const bad = axe.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical');
      result.axe[route] = bad.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length }));
      result.axeCompleted.push(route);

      for (const w of WIDTHS) {
        await page.setViewportSize({ width: w, height: 900 });
        await page.waitForTimeout(500);
        const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth }));
        result.widthProbes[route].push(w);
        if (o.sw > o.cw + 1) result.overflow.push({ route, width: w, scrollWidth: o.sw });
        if (w === 320) await page.screenshot({ path: path.join(shots, `${slug(route)}-320.png`), fullPage: true });
      }
      entry.ok = true;
    } catch (e) {
      entry.ok = false; entry.error = String(e).slice(0, 300);
    }
    result.routes.push(entry);
  }
} catch (e) {
  result.fatal = String(e).slice(0, 500);
}
await browser.close();

// Lighthouse, desktop preset, on the entry URL with a fresh profile.
let chrome;
try {
  chrome = await chromeLauncher.launch({ chromePath: chromium.executablePath(), chromeFlags: ['--headless=new'] });
  const run = await lighthouse(baseUrl, { port: chrome.port, onlyCategories: ['performance', 'accessibility'], logLevel: 'error' }, desktopConfig);
  const c = run.lhr.categories;
  result.lighthouse = { performance: Math.round(c.performance.score * 100), accessibility: Math.round(c.accessibility.score * 100) };
} catch (e) {
  result.lighthouse = { error: String(e).slice(0, 300) };
} finally {
  if (chrome) await chrome.kill();
}

fs.writeFileSync(path.join(outDir, 'browser.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify({ demoLoaded: result.demoLoaded, routes: result.routes.length, consoleErrors: result.consoleErrors.length, overflow: result.overflow.length, lighthouse: result.lighthouse }));
