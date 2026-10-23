import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { buildSite } from '../scripts/build.mjs';
import { createStaticServer } from '../scripts/dev.mjs';
import { getConfig } from '../site.config.mjs';

function decodeAttribute(value) {
  return value.replaceAll('&amp;', '&').replaceAll('&quot;', '"').replaceAll('&#39;', "'").replaceAll('&lt;', '<').replaceAll('&gt;', '>');
}

function references(html) {
  const result = [];
  for (const tag of html.matchAll(/<(?:a|link|script|img|source)\b[^>]*>/g)) {
    for (const attribute of tag[0].matchAll(/\b(?:href|src)="([^"]*)"/g)) result.push(decodeAttribute(attribute[1]));
  }
  for (const image of html.matchAll(/<meta\b[^>]*property="og:image"[^>]*content="([^"]+)"/g)) result.push(decodeAttribute(image[1]));
  return result;
}

test('real website output serves every local navigation and asset reference under a hosting prefix', async (t) => {
  const directory = await mkdtemp(path.join(tmpdir(), 'mixer-web-site-'));
  let server;
  t.after(async () => {
    if (server) await new Promise((resolve) => server.close(resolve));
    await rm(directory, { recursive: true, force: true });
  });
  const config = getConfig({ SITE_BASE_PATH: '/preview/' });
  const result = await buildSite({ config, distDir: path.join(directory, 'dist') });
  server = await createStaticServer({ distDir: result.distDir, basePath: config.basePath });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const pageFiles = ['index.html', 'docs/index.html', 'privacy/index.html', '404.html'];
  const observed = new Set();
  for (const filename of pageFiles) {
    const html = await readFile(path.join(result.distDir, filename), 'utf8');
    assert.match(html, /<html\b[^>]*\blang="en(?:-US)?"/i, filename);
    assert.match(html, /name="viewport"/, filename);
    assert.doesNotMatch(html, /\{\{[A-Z_]+\}\}/, filename);
    assert.match(html, /content="noindex, nofollow"/, filename);
    const route = filename === 'index.html' ? '' : filename.replace(/index\.html$/, '');
    const pageUrl = new URL(`${config.basePath}${route}`, origin);
    for (const reference of references(html)) {
      if (!reference || reference.startsWith('mailto:') || reference.startsWith('tel:') || reference.startsWith('data:')) continue;
      const target = new URL(reference, pageUrl);
      if (target.origin === config.origin) target.host = new URL(origin).host;
      if (target.origin !== origin) continue;
      assert.ok(target.pathname.startsWith(config.basePath), `${filename}: reference escapes hosting prefix: ${reference}`);
      const key = `${target.pathname}${target.search}${target.hash}`;
      if (observed.has(key)) continue;
      observed.add(key);
      const response = await fetch(target);
      assert.equal(response.status, 200, `${filename}: ${reference}`);
      if (target.hash && response.headers.get('content-type')?.startsWith('text/html')) {
        const destination = await response.text();
        const identifiers = new Set([...destination.matchAll(/\bid="([^"]+)"/g)].map((match) => decodeAttribute(match[1])));
        assert.ok(identifiers.has(decodeURIComponent(target.hash.slice(1))), `${filename}: missing anchor ${reference}`);
      }
    }
  }
  assert.ok(observed.has('/preview/styles.css'));
  assert.ok(observed.has('/preview/app.js'));
  assert.ok(observed.has('/preview/docs/'));
  assert.ok(observed.has('/preview/privacy/'));
  const manifestResponse = await fetch(`${origin}/preview/site.webmanifest`);
  const manifest = await manifestResponse.json();
  for (const icon of manifest.icons) {
    assert.ok(icon.src.startsWith(config.basePath));
    assert.equal((await fetch(new URL(icon.src, origin))).status, 200, icon.src);
  }
  const missing = await fetch(`${origin}/preview/this-page-does-not-exist`);
  assert.equal(missing.status, 404);
  assert.match(await missing.text(), /not found|couldn.t find|lost/i);
});
