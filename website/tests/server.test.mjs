import test from 'node:test';
import assert from 'node:assert/strict';
import { request } from 'node:http';
import { mkdtemp, mkdir, writeFile, rm, symlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createStaticServer } from '../scripts/dev.mjs';

function get(port, pathname, method = 'GET') {
  return new Promise((resolve, reject) => {
    const req = request({ host: '127.0.0.1', port, path: pathname, method }, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => resolve({ status: response.statusCode, headers: response.headers, body: Buffer.concat(chunks).toString() }));
      response.on('error', reject);
    });
    req.on('error', reject);
    req.end();
  });
}

async function setup(t, basePath = '/') {
  const temporary = await mkdtemp(path.join(tmpdir(), 'mixer-web-http-'));
  const distDir = path.join(temporary, 'dist');
  await mkdir(path.join(distDir, 'docs'), { recursive: true });
  await mkdir(path.join(distDir, 'assets'), { recursive: true });
  await writeFile(path.join(distDir, 'index.html'), '<h1>Mixer</h1>');
  await writeFile(path.join(distDir, 'docs/index.html'), '<h1>Documentation</h1>');
  await writeFile(path.join(distDir, '404.html'), '<h1>Page not found</h1>');
  await writeFile(path.join(distDir, 'assets/fox.svg'), '<svg/>');
  await writeFile(path.join(distDir, 'app.js'), 'console.log("Mixer");');
  await writeFile(path.join(temporary, 'private.txt'), 'do not serve this');
  const server = await createStaticServer({ distDir, basePath });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(async () => {
    await new Promise((resolve) => server.close(resolve));
    await rm(temporary, { recursive: true, force: true });
  });
  return { port: server.address().port, distDir, temporary };
}

test('serves document routes, MIME types, HEAD, and useful security headers over HTTP', async (t) => {
  const { port } = await setup(t);
  const home = await get(port, '/');
  assert.equal(home.status, 200);
  assert.equal(home.body, '<h1>Mixer</h1>');
  assert.equal(home.headers['content-type'], 'text/html; charset=utf-8');
  assert.equal(home.headers['cache-control'], 'no-store');
  assert.equal(home.headers['x-content-type-options'], 'nosniff');
  assert.match(home.headers['x-robots-tag'], /noindex/);
  assert.match(home.headers['content-security-policy'], /frame-ancestors 'none'/);
  const docs = await get(port, '/docs?from=home');
  assert.equal(docs.status, 308);
  assert.equal(docs.headers.location, '/docs/');
  assert.match((await get(port, '/docs/')).body, /Documentation/);
  assert.equal((await get(port, '/assets/fox.svg')).headers['content-type'], 'image/svg+xml');
  assert.equal((await get(port, '/app.js')).headers['content-type'], 'text/javascript; charset=utf-8');
  const head = await get(port, '/', 'HEAD');
  assert.equal(head.status, 200);
  assert.equal(head.body, '');
  assert.equal(Number(head.headers['content-length']), Buffer.byteLength(home.body));
  const post = await get(port, '/', 'POST');
  assert.equal(post.status, 405);
  assert.equal(post.headers.allow, 'GET, HEAD');
});

test('missing paths return a real 404, including outside an optional hosting prefix', async (t) => {
  const { port } = await setup(t, '/preview/');
  assert.equal((await get(port, '/preview')).headers.location, '/preview/');
  assert.equal((await get(port, '/preview/')).status, 200);
  assert.equal((await get(port, '/preview/docs')).headers.location, '/preview/docs/');
  for (const route of ['/', '/docs/', '/preview/missing', '/preview/assets/']) {
    const result = await get(port, route);
    assert.equal(result.status, 404, route);
    assert.match(result.body, /Page not found/);
  }
});

test('raw traversal, encoded traversal, malformed URLs, and escaping symlinks cannot expose files', async (t) => {
  const { port, distDir, temporary } = await setup(t);
  await symlink(path.join(temporary, 'private.txt'), path.join(distDir, 'leak.txt'));
  await symlink(temporary, path.join(distDir, 'escape'));
  for (const route of ['/../private.txt', '/%2e%2e/private.txt', '/docs/%2e%2e/%2e%2e/private.txt', '/docs%2f..%2f..%2fprivate.txt', '/leak.txt', '/escape/private.txt']) {
    const result = await get(port, route);
    assert.equal(result.status, 403, route);
    assert.doesNotMatch(result.body, /do not serve this/);
  }
  for (const route of ['/%FF', '/%00', '/docs%5cprivate']) assert.equal((await get(port, route)).status, 400, route);
});
