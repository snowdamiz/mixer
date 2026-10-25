import assert from 'node:assert/strict';
import test from 'node:test';
import { pathToFileURL } from 'node:url';
const { renderReviewRoute, renderMissingProvider } = await import(pathToFileURL(process.env.MIXER_REVIEW_SSR));
const render = (url, session) => renderReviewRoute(url, session).replace(/<!--[^]*?-->/g, '');

test('workspace production route composes branded navigation, semantic directory, and honest session states', () => {
  for (const [session, message] of [[undefined, 'Workspace temporarily unavailable'], [{ kind: 'unavailable' }, 'Workspace temporarily unavailable'],
    [{ kind: 'unauthenticated' }, 'Sign in to view your workspace']]) {
    const html = render('/workspace', session);
    assert.match(html, /src="\/assets\/flick-128.webp"/);
    assert.match(html, /mixer<span class="brand-period">\.<\/span>/);
    assert.match(html, /<main id="main-content" tabindex="-1">/);
    assert.match(html, /href="\/workspace"[^>]*aria-current="page"/);
    assert.match(html, /id="workspace-directory-heading"/);
    assert.ok(html.includes(message));
    assert.doesNotMatch(html, /private:|Sign out|Create organization|fixture/);
  }
});

test('server-rendered ready session remains non-fetching and serializes no adapter data', () => {
  let calls = 0;
  const client = { organizations() { calls++; throw Error('private:token'); }, projects() { calls++; throw Error('private:token'); } };
  const html = render('/workspace?private:query=not-data', { kind: 'ready', client });
  assert.equal(calls, 0); assert.match(html, /Loading organizations/);
  assert.doesNotMatch(html, /private:|token|organizations\(\)|projects\(\)/);
});

test('release, build, unknown and production-only preview paths have correct route content', () => {
  for (const url of ['/releases', '/builds', '/unknown', '/preview/builds', '/preview/release-checks']) {
    const html = render(url);
    assert.match(html, /href="\/workspace"/); assert.doesNotMatch(html, /id="workspace-directory-heading"/);
    if (url === '/releases') assert.match(html, /Release checks/);
    else if (url === '/builds') assert.match(html, /Builds/);
    else assert.match(html, /<h1>Page not found<\/h1>/);
  }
});

test('an unowned workspace consumer fails closed', () => {
  assert.throws(() => renderMissingProvider(), /Missing workspace owner/);
});

test('workspace query, fragment and trailing slash preserve directory and shell section naming', () => {
  for (const url of ['/workspace?tab=organizations', '/workspace#projects', '/workspace/']) {
    const html = render(url);
    assert.match(html, /<strong>Organizations &amp; projects<\/strong>/);
    assert.match(html, /id="workspace-directory-heading"/);
    assert.doesNotMatch(html, /<strong>Page not found<\/strong>/);
  }
});
