import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, rm, readdir, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { buildSite } from '../scripts/build.mjs';
import { getConfig } from '../site.config.mjs';

async function fixture(t) {
  const directory = await mkdtemp(path.join(tmpdir(), 'mixer-web-build-'));
  const srcDir = path.join(directory, 'src');
  const publicDir = path.join(directory, 'public');
  const distDir = path.join(directory, 'dist');
  await mkdir(path.join(srcDir, 'docs'), { recursive: true });
  await mkdir(path.join(srcDir, 'privacy'), { recursive: true });
  await mkdir(path.join(publicDir, 'assets'), { recursive: true });
  const html = '<!doctype html><html lang="en"><head>{{SEO_HEAD}}<link rel="stylesheet" href="{{BASE}}styles.css"></head><body><a href="{{BASE}}">Home</a><a href="{{SIGNUP_URL}}">Start</a><a href="{{REPO_URL}}">Code</a><footer>{{YEAR}}</footer><script src="{{BASE}}app.js" defer></script></body></html>';
  for (const filename of ['index.html', 'docs/index.html', 'privacy/index.html', '404.html']) await writeFile(path.join(srcDir, filename), html);
  await writeFile(path.join(srcDir, 'app.js'), 'const base = "{{BASE}}";');
  await writeFile(path.join(srcDir, 'styles.css'), 'body { background-image: url("{{BASE}}assets/fox.svg"); }');
  await writeFile(path.join(srcDir, 'docs.css'), 'main { max-width: 70ch; }');
  const asset = Buffer.from([0, 1, 2, 255, 128]);
  await writeFile(path.join(publicDir, 'assets/fox.bin'), asset);
  await writeFile(path.join(publicDir, 'assets/fox.svg'), '<svg xmlns="http://www.w3.org/2000/svg"/>');
  t.after(() => rm(directory, { recursive: true, force: true }));
  return { directory, srcDir, publicDir, distDir, asset };
}

function attributes(html, tag) {
  // This scanner only reads attributes for output-link verification; it never
  // decides product capability, release compatibility, or execution authority.
  return [...html.matchAll(new RegExp(`<${tag}\\b[^>]*?\\b(?:href|src)="([^"]+)"`, 'g'))].map((match) => match[1].replaceAll('&amp;', '&'));
}

test('build produces a complete private preview with substituted links and unchanged public assets', async (t) => {
  const options = await fixture(t);
  const result = await buildSite({ ...options, config: getConfig({}) });
  assert.equal(result.config.production, false);
  for (const filename of ['index.html', 'docs/index.html', 'privacy/index.html', '404.html', 'robots.txt', 'sitemap.xml', 'site.webmanifest']) assert.ok(result.files.includes(filename), filename);
  const home = await readFile(path.join(options.distDir, 'index.html'), 'utf8');
  assert.doesNotMatch(home, /\{\{[A-Z_]+\}\}/);
  assert.match(home, /content="noindex, nofollow"/);
  assert.ok(attributes(home, 'a').includes('/docs/'));
  assert.match(home, /<footer>\d{4}<\/footer>/);
  assert.equal(await readFile(path.join(options.distDir, 'app.js'), 'utf8'), 'const base = "/";');
  assert.deepEqual(await readFile(path.join(options.distDir, 'assets/fox.bin')), options.asset);
  assert.match(await readFile(path.join(options.distDir, 'robots.txt'), 'utf8'), /Disallow: \//);
  assert.doesNotMatch(await readFile(path.join(options.distDir, 'sitemap.xml'), 'utf8'), /<loc>/);
  assert.equal(JSON.parse(await readFile(path.join(options.distDir, 'site.webmanifest'), 'utf8')).start_url, '/');
});

test('production output mounts navigation, canonical metadata, generated search files, and asset paths consistently', async (t) => {
  const options = await fixture(t);
  const config = getConfig({ SITE_URL: 'https://mixer.tools', SITE_BASE_PATH: '/v1.0/preview/', SIGNUP_URL: 'https://join.mixer.tools/?from=site&flow=start' }, { production: true });
  await buildSite({ ...options, config });
  const home = await readFile(path.join(options.distDir, 'index.html'), 'utf8');
  const docs = await readFile(path.join(options.distDir, 'docs/index.html'), 'utf8');
  const missing = await readFile(path.join(options.distDir, '404.html'), 'utf8');
  assert.ok(attributes(home, 'a').includes('/v1.0/preview/'));
  assert.ok(attributes(home, 'a').includes('https://join.mixer.tools/?from=site&flow=start'));
  assert.ok(attributes(home, 'script').includes('/v1.0/preview/app.js'));
  assert.ok(attributes(docs, 'link').includes('https://mixer.tools/v1.0/preview/docs/'));
  assert.match(home, /content="index, follow, max-image-preview:large"/);
  assert.match(missing, /content="noindex, nofollow"/);
  assert.match(await readFile(path.join(options.distDir, 'styles.css'), 'utf8'), /\/v1\.0\/preview\/assets\/fox\.svg/);
  const sitemap = await readFile(path.join(options.distDir, 'sitemap.xml'), 'utf8');
  for (const route of ['', 'docs/', 'privacy/']) assert.ok(sitemap.includes(`https://mixer.tools/v1.0/preview/${route}`), route);
  assert.doesNotMatch(sitemap, /404/);
  assert.match(await readFile(path.join(options.distDir, 'robots.txt'), 'utf8'), /Sitemap: https:\/\/mixer.tools\/v1\.0\/preview\/sitemap.xml/);
  const manifest = JSON.parse(await readFile(path.join(options.distDir, 'site.webmanifest'), 'utf8'));
  assert.equal(manifest.scope, '/v1.0/preview/');
  assert.equal(manifest.icons[0].src, '/v1.0/preview/assets/icon-192.png');
});

test('source defects fail the build and preserve the last successful output', async (t) => {
  const options = await fixture(t);
  const config = getConfig({});
  await buildSite({ ...options, config });
  const original = await readFile(path.join(options.distDir, 'index.html'), 'utf8');
  await writeFile(path.join(options.srcDir, 'index.html'), '{{UNKNOWN_TOKEN}}');
  await assert.rejects(buildSite({ ...options, config }), /missing \{\{SEO_HEAD\}\}/);
  assert.equal(await readFile(path.join(options.distDir, 'index.html'), 'utf8'), original);
  assert.deepEqual((await readdir(options.directory)).filter((file) => file.includes('.building-')), []);
  await writeFile(path.join(options.srcDir, 'index.html'), '<head>{{SEO_HEAD}}</head>{{UNKNOWN_TOKEN}}');
  await assert.rejects(buildSite({ ...options, config }), /Unresolved template token/);
  await rm(path.join(options.srcDir, 'docs.css'));
  await assert.rejects(buildSite({ ...options, config }), /Missing website source: docs.css/);
});

test('public collisions and symbolic links are rejected before replacing output', async (t) => {
  const options = await fixture(t);
  const config = getConfig({});
  await buildSite({ ...options, config });
  await writeFile(path.join(options.publicDir, 'index.html'), 'bad override');
  await assert.rejects(buildSite({ ...options, config }), /Source and public files collide/);
  await rm(path.join(options.publicDir, 'index.html'));
  await writeFile(path.join(options.publicDir, 'robots.txt'), 'bad metadata override');
  await assert.rejects(buildSite({ ...options, config }), /Generated website file collides/);
  await rm(path.join(options.publicDir, 'robots.txt'));
  await symlink(path.join(options.directory, 'src/index.html'), path.join(options.publicDir, 'leak.html'));
  await assert.rejects(buildSite({ ...options, config }), /Symbolic links are not accepted/);
  assert.doesNotMatch(await readFile(path.join(options.distDir, 'index.html'), 'utf8'), /bad override/);
});
