import test from 'node:test';
import assert from 'node:assert/strict';
import { getConfig, normalizeBasePath } from '../site.config.mjs';

const production = { production: true };

test('preview configuration is explicitly private and has useful local destinations', () => {
  const config = getConfig({});
  assert.equal(config.origin, 'http://localhost:4173');
  assert.equal(config.basePath, '/');
  assert.equal(config.siteUrl, 'http://localhost:4173/');
  assert.equal(config.signupUrl, '/docs/');
  assert.equal(config.repoUrl, 'https://github.com/snowdamiz/mixer');
  assert.equal(config.production, false);
  assert.equal(Object.isFrozen(config), true);
  assert.equal(getConfig({ NODE_ENV: 'production', SITE_URL: 'https://mixer.tools' }).production, false);
});

test('production requires an explicit public HTTPS origin', () => {
  for (const SITE_URL of [undefined, '', 'http://mixer.tools', 'https://localhost', 'https://localhost.', 'https://10.0.0.1', 'https://example.com.', 'https://example', 'https://mixer', 'https://127.0.0.1', 'https://[::1]', 'https://example.com', 'https://www.example.org', 'https://mixer.invalid', 'https://mixer.test']) {
    assert.throws(() => getConfig({ SITE_URL }, production), /SITE_URL/);
  }
  const config = getConfig({ SITE_URL: 'https://mixer.tools/' }, production);
  assert.equal(config.origin, 'https://mixer.tools');
  assert.equal(config.siteUrl, 'https://mixer.tools/');
  assert.equal(config.production, true);
});

test('origin and CTA validation rejects credentials, malformed values, and ambiguous path configuration', () => {
  for (const SITE_URL of ['javascript:alert(1)', '//mixer.tools', 'https://user:secret@mixer.tools', 'https://mixer.tools/docs/', 'https://mixer.tools/?secret=value', 'https://mixer.tools/#fragment']) {
    assert.throws(() => getConfig({ SITE_URL }), /SITE_URL/);
  }
  for (const SIGNUP_URL of ['//untrusted.invalid', 'javascript:alert(1)', '/docs/../privacy/', '/%2e%2e/private', '/docs/" onclick="alert(1)', '/docs/\\private']) {
    assert.throws(() => getConfig({ SIGNUP_URL }), /SIGNUP_URL/);
  }
  assert.throws(() => getConfig({ SITE_URL: 'https://mixer.tools', SIGNUP_URL: 'http://signup.mixer.tools' }, production), /HTTPS/);
  assert.throws(() => getConfig({ REPO_URL: 'http://github.com/snowdamiz/mixer' }), /HTTPS/);
});

test('base paths normalize safely and mount navigation under the same prefix', () => {
  for (const value of ['mixer', '/mixer', '/mixer/']) assert.equal(normalizeBasePath(value), '/mixer/');
  for (const value of ['/../secret/', '/./', '/one//two/', '/a%2fb/', '/a?query/', '/a#hash/', '/a\\b/', '/two words/']) {
    assert.throws(() => normalizeBasePath(value), /SITE_BASE_PATH/);
  }
  const config = getConfig({ SITE_URL: 'https://mixer.tools', SITE_BASE_PATH: 'v1.0/preview', SIGNUP_URL: '/docs/?from=landing' }, production);
  assert.equal(config.basePath, '/v1.0/preview/');
  assert.equal(config.siteUrl, 'https://mixer.tools/v1.0/preview/');
  assert.equal(config.signupUrl, '/v1.0/preview/docs/?from=landing');
  assert.equal(getConfig({ SIGNUP_URL: 'https://join.mixer.tools/?source=site' }).signupUrl, 'https://join.mixer.tools/?source=site');
});
