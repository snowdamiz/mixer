import { isIP } from 'node:net';

const DEFAULT_ORIGIN = 'http://localhost:4173';

function absoluteUrl(value, label, { production = false } = {}) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error(`${label} must be an absolute URL.`);
  }
  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new Error(`${label} must be an HTTP(S) URL without credentials.`);
  }
  if (production && url.protocol !== 'https:') {
    throw new Error(`${label} must use HTTPS in production.`);
  }
  return url;
}

export function normalizeBasePath(value = '/') {
  const input = String(value).trim();
  if (!input || input === '/') return '/';
  const parts = input.replace(/^\/+|\/+$/g, '').split('/');
  if (parts.some((part) => !/^[A-Za-z0-9._~-]+$/.test(part) || part === '.' || part === '..')) {
    throw new Error('SITE_BASE_PATH must contain safe path segments, for example /mixer/.');
  }
  return `/${parts.join('/')}/`;
}

function mountedUrl(value, basePath, production, label) {
  const input = String(value).trim();
  if (input.startsWith('/') && !input.startsWith('//')) {
    const url = new URL(input, 'https://local.invalid');
    if (url.pathname !== input.split(/[?#]/, 1)[0] || input.includes('\\') || /[\u0000-\u0020"'<>]/.test(input)) {
      throw new Error(`${label} must be a safe root-relative path or absolute URL.`);
    }
    return `${basePath}${input.slice(1)}`;
  }
  const url = absoluteUrl(input, label, { production });
  return url.href;
}

export function getConfig(env = process.env, { production = false } = {}) {
  if (production && !env.SITE_URL?.trim()) {
    throw new Error('Production builds require an explicit HTTPS SITE_URL. Use npm run build for a private local preview.');
  }
  const url = absoluteUrl(env.SITE_URL?.trim() || DEFAULT_ORIGIN, 'SITE_URL', { production });
  if (url.pathname !== '/' || url.search || url.hash) {
    throw new Error('SITE_URL must be an origin with no path, query, or fragment. Set SITE_BASE_PATH separately.');
  }
  if (production) {
    const hostname = url.hostname.toLowerCase().replace(/\.$/, '');
    if (isIP(hostname.replace(/^\[|\]$/g, '')) || !hostname.includes('.') || hostname === 'localhost' || hostname.endsWith('.localhost') || hostname.endsWith('.local') ||
        hostname === '0.0.0.0' || hostname === '[::1]' || /^127\./.test(hostname) ||
        hostname === 'example.com' || hostname.endsWith('.example.com') ||
        hostname === 'example.org' || hostname.endsWith('.example.org') ||
        hostname === 'example.net' || hostname.endsWith('.example.net') ||
        hostname.endsWith('.example') || hostname.endsWith('.invalid') || hostname.endsWith('.test')) {
      throw new Error('Production SITE_URL must use your real public domain, not a local or example host.');
    }
  }
  const basePath = normalizeBasePath(env.SITE_BASE_PATH);
  const repo = absoluteUrl(env.REPO_URL?.trim() || 'https://github.com/snowdamiz/mixer', 'REPO_URL', { production: true });
  const config = {
    name: 'Mixer',
    origin: url.origin,
    basePath,
    siteUrl: `${url.origin}${basePath}`,
    production,
    signupUrl: mountedUrl(env.SIGNUP_URL?.trim() || '/docs/', basePath, production, 'SIGNUP_URL'),
    repoUrl: repo.href,
    title: 'Mixer — Native iOS & Android apps, built with Swift',
    description: 'Build beautiful native apps for iOS and Android with Swift. Ship thoughtful experiences, share your code, and deliver signed updates with confidence.',
  };
  return Object.freeze(config);
}

export const siteConfig = getConfig();
