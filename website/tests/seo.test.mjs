import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createSearchFiles, createSeoHead } from '../scripts/seo.mjs';

const production = Object.freeze({
  name: 'Mixer',
  origin: 'https://example.org',
  basePath: '/',
  siteUrl: 'https://example.org/',
  production: true,
  signupUrl: '/docs/',
  repoUrl: 'https://github.com/snowdamiz/mixer',
  title: 'Mixer — Swift in. Native out.',
  description: 'Build native iOS and Android apps with shared Swift and controlled releases.'
});

const head = (pathname, changes = {}) => createSeoHead({ pathname, config: { ...production, ...changes } });
const graph = markup => JSON.parse(markup.match(/<script type="application\/ld\+json">([^]*?)<\/script>/)[1])['@graph'];
const store = JSON.parse(await readFile(new URL('../marketing/app-store.json', import.meta.url), 'utf8'));

test('home head has the configured title, description, and exactly one canonical', () => {
  const markup = head('/');
  assert.ok(markup.includes(`<title>${production.title}</title>`));
  assert.ok(markup.includes(`name="description" content="${production.description}"`));
  assert.equal(markup.match(/rel="canonical"/g).length, 1);
  assert.ok(markup.includes('rel="canonical" href="https://example.org/"'));
  assert.ok(markup.includes('content="index, follow, max-image-preview:large"'));
});

test('documentation and privacy have distinct metadata and normalized route canonicals', () => {
  const docs = head('/docs?ref=campaign#start');
  const privacy = head('/privacy/index.html');
  assert.match(docs, /<title>Documentation \| Mixer<\/title>/);
  assert.match(privacy, /<title>Privacy \| Mixer<\/title>/);
  assert.match(docs, /rel="canonical" href="https:\/\/example.org\/docs\/"/);
  assert.match(privacy, /rel="canonical" href="https:\/\/example.org\/privacy\/"/);
  assert.ok(!docs.includes('ref=campaign'));
  const breadcrumb = graph(docs).find(node => node['@type'] === 'BreadcrumbList');
  assert.deepEqual(breadcrumb.itemListElement.map(item => item.item), ['https://example.org/', 'https://example.org/docs/']);
});

test('404 and unknown routes are unindexable and emit no canonical or misleading page graph', () => {
  for (const pathname of ['/404.html', '/removed/', '//outside.example/', '/%3Cscript%3E']) {
    const markup = head(pathname);
    assert.match(markup, /<title>Page not found \| Mixer<\/title>/);
    assert.ok(markup.includes('content="noindex, nofollow"'));
    assert.ok(!markup.includes('rel="canonical"'));
    assert.ok(!markup.includes('property="og:url"'));
    assert.ok(!markup.includes('application/ld+json'));
  }
});

test('preview is fail-closed even with a configured future public origin', () => {
  const markup = head('/', { production: false });
  const files = createSearchFiles({ ...production, production: false });
  assert.ok(markup.includes('content="noindex, nofollow"'));
  assert.equal(files['robots.txt'], 'User-agent: *\nDisallow: /\n');
  assert.ok(!files['sitemap.xml'].includes('<url>'));
});

test('a missing production flag, HTTP origin, or loopback host stays unindexable', () => {
  const configs = [
    { ...production, production: undefined },
    { ...production, origin: 'http://example.org', siteUrl: 'http://example.org/' },
    { ...production, origin: 'https://localhost', siteUrl: 'https://localhost/' },
    { ...production, origin: 'https://preview.localhost', siteUrl: 'https://preview.localhost/' },
    { ...production, origin: 'https://127.0.0.1', siteUrl: 'https://127.0.0.1/' },
    { ...production, origin: 'https://[::1]', siteUrl: 'https://[::1]/' }
  ];
  for (const config of configs) {
    assert.ok(createSeoHead({ pathname: '/', config }).includes('content="noindex, nofollow"'));
    assert.ok(!createSearchFiles(config)['sitemap.xml'].includes('<url>'));
  }
});

test('social previews have absolute URLs, dimensions, type, and useful alt text', () => {
  const markup = head('/');
  for (const snippet of [
    'property="og:image" content="https://example.org/assets/og-mixer.png"',
    'property="og:image:width" content="1200"',
    'property="og:image:height" content="630"',
    'property="og:image:type" content="image/png"',
    'name="twitter:card" content="summary_large_image"',
    'name="twitter:image" content="https://example.org/assets/og-mixer.png"',
    'property="og:image:alt" content="Flick,',
    'name="twitter:image:alt" content="Flick,',
    'name="theme-color" content="#f8f7f4"'
  ]) assert.ok(markup.includes(snippet), snippet);
  assert.ok(!markup.includes('twitter:site'));
  assert.ok(!markup.includes('apple-itunes-app'));
});

test('head text is escaped and JSON-LD cannot break out of its script element', () => {
  const injected = `Mixer </script><script>alert("x")</script> & 'fox' \u2028\u2029`;
  const markup = head('/', { name: injected, title: injected, description: injected });
  assert.ok(!markup.includes('<script>alert'));
  assert.ok(markup.includes('&lt;/script&gt;'));
  assert.ok(markup.includes('&amp; &#39;fox&#39;'));
  assert.equal(markup.match(/<script /g).length, 1);
  assert.equal(markup.match(/<\/script>/g).length, 1);
  assert.ok(markup.includes('\\u003c/script\\u003e'));
  assert.ok(markup.includes('\\u2028\\u2029'));
  const software = graph(markup).find(node => node['@type'] === 'SoftwareApplication');
  assert.equal(software.name, injected);
  assert.equal(software.description, injected);
});

test('JSON-LD identifies developer tooling without unsupported review, price, or store claims', () => {
  const data = graph(head('/'));
  const software = data.find(node => node['@type'] === 'SoftwareApplication');
  assert.equal(software.applicationCategory, 'DeveloperApplication');
  assert.equal(software.url, production.siteUrl);
  assert.ok(data.some(node => node['@type'] === 'Organization'));
  assert.ok(data.some(node => node['@type'] === 'WebSite'));
  for (const key of ['aggregateRating', 'review', 'offers', 'installUrl', 'downloadUrl', 'operatingSystem']) {
    assert.equal(software[key], undefined);
  }
});

test('all search URLs and assets respect a safe nested base path', () => {
  const config = { ...production, basePath: '/v1.0/mixer~preview/', siteUrl: 'https://example.org/v1.0/mixer~preview/' };
  const markup = createSeoHead({ pathname: '/docs/', config });
  const files = createSearchFiles(config);
  assert.ok(markup.includes('rel="canonical" href="https://example.org/v1.0/mixer~preview/docs/"'));
  assert.ok(markup.includes('content="https://example.org/v1.0/mixer~preview/assets/og-mixer.png"'));
  assert.ok(markup.includes('href="https://example.org/v1.0/mixer~preview/site.webmanifest"'));
  assert.ok(files['robots.txt'].includes('Sitemap: https://example.org/v1.0/mixer~preview/sitemap.xml'));
  const sitemapUrls = [...files['sitemap.xml'].matchAll(/<loc>([^<]+)<\/loc>/g)].map(match => match[1]);
  assert.deepEqual(sitemapUrls, ['', 'docs/', 'privacy/'].map(path => `${config.siteUrl}${path}`));
  const manifest = JSON.parse(files['site.webmanifest']);
  assert.equal(manifest.id, config.basePath);
  assert.equal(manifest.start_url, config.basePath);
  assert.equal(manifest.scope, config.basePath);
  assert.ok(manifest.icons.every(icon => icon.src.startsWith(`${config.basePath}assets/`)));
});

test('production sitemap includes only intended pages and no invented modification dates', () => {
  const files = createSearchFiles(production);
  assert.ok(files['sitemap.xml'].startsWith('<?xml version="1.0" encoding="UTF-8"?>'));
  assert.equal(files['sitemap.xml'].match(/<url>/g).length, 3);
  assert.ok(!files['sitemap.xml'].includes('404'));
  assert.ok(!files['sitemap.xml'].includes('lastmod'));
  assert.equal(files['robots.txt'], 'User-agent: *\nAllow: /\n\nSitemap: https://example.org/sitemap.xml\n');
});

test('manifest is valid JSON with browser icons and no native store associations', () => {
  const manifest = JSON.parse(createSearchFiles(production)['site.webmanifest']);
  assert.equal(manifest.name, 'Mixer');
  assert.equal(manifest.display, 'standalone');
  assert.deepEqual(manifest.icons.map(icon => icon.sizes), ['192x192', '512x512']);
  assert.ok(manifest.icons.every(icon => icon.type === 'image/png' && icon.purpose === 'any'));
  assert.equal(manifest.related_applications, undefined);
  assert.equal(manifest.prefer_related_applications, undefined);
});

test('invalid origins, traversal, and contradictory site URLs fail the build', () => {
  for (const changes of [
    { origin: 'javascript:alert(1)' },
    { origin: 'https://user:password@example.org' },
    { origin: 'https://example.org/path' },
    { origin: 'https://example.org?query=1' },
    { basePath: 'mixer/' },
    { basePath: '//outside.example/' },
    { basePath: '/mixer/../' },
    { basePath: '/./' },
    { basePath: '/%2e%2e/' },
    { basePath: '/mixer"/' },
    { siteUrl: 'https://unconfigured.example/' }
  ]) assert.throws(() => createSearchFiles({ ...production, ...changes }), TypeError);
});

test('FieldLog Apple metadata fits live character and byte limits', () => {
  const apple = store.apple;
  for (const [key, max] of Object.entries({ name: 30, subtitle: 30, promotionalText: 170, description: 4000 })) {
    assert.ok(apple[key].length > 0 && [...apple[key]].length <= max, `${key} exceeds ${max} characters`);
  }
  assert.ok(apple.name.length >= 2);
  assert.ok(Buffer.byteLength(apple.keywords, 'utf8') <= 100, 'Apple keywords exceed 100 UTF-8 bytes');
  const keywords = apple.keywords.split(',');
  assert.equal(new Set(keywords).size, keywords.length);
  assert.ok(keywords.every(keyword => keyword.length > 2 && keyword === keyword.trim()));
  assert.ok(!apple.description.includes('<'));
});

test('FieldLog Play metadata and six-screen story are complete editable collateral', () => {
  for (const [key, max] of Object.entries({ title: 30, shortDescription: 80, fullDescription: 4000 })) {
    assert.ok(store.googlePlay[key].length > 0 && [...store.googlePlay[key]].length <= max, `${key} exceeds ${max} characters`);
  }
  assert.equal(store.product, 'FieldLog');
  assert.equal(store.status, 'editable-draft-requires-release-qualification');
  assert.equal(store.publication.appStoreUrl, null);
  assert.equal(store.publication.googlePlayUrl, null);
  assert.equal(store.publication.reviewStatus, 'not-submitted-by-this-work');
  assert.equal(store.screenshotStory.length, 6);
  assert.deepEqual(store.screenshotStory.map(screen => screen.order), [1, 2, 3, 4, 5, 6]);
  assert.ok(store.screenshotStory.every(screen => screen.capture && screen.qualification && screen.caption && screen.alt.length <= 140));
  assert.ok(store.publicationChecklist.every(item => item.status === 'pending'));
});
