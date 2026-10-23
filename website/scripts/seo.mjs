/** Build-time discovery metadata. No client JavaScript or third-party services. */
const PAGE_DETAILS = Object.freeze({
  '/docs/': {
    title: 'Documentation | Mixer',
    description: 'Get started with Mixer: shared Swift, native iOS and Android UI, local and managed builds, and compatible over-the-air releases.'
  },
  '/privacy/': {
    title: 'Privacy | Mixer',
    description: 'Learn how this Mixer website handles your data, browser storage, external links, and contact information.'
  },
  '/404.html': {
    title: 'Page not found | Mixer',
    description: 'This page could not be found. Explore Mixer, the Swift-first platform for native iOS and Android apps, or visit the documentation.'
  }
});

const INDEXABLE_PATHS = ['/', '/docs/', '/privacy/'];
const IMAGE_ALT = 'Flick, the Mixer fox, beside Write Swift. Ship both. One codebase. Native iOS and Android.';

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, character => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[character]);
}

function serializeJson(value) {
  // A JSON string may contain a closing script tag. Escape HTML delimiters before
  // embedding it in a script element, including arbitrary configuration text.
  return JSON.stringify(value)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026')
    .replace(/\u2028/g, '\\u2028')
    .replace(/\u2029/g, '\\u2029');
}

function settings(config) {
  if (!config || typeof config !== 'object') throw new TypeError('SEO configuration is required');
  const origin = new URL(config.origin);
  if (!['https:', 'http:'].includes(origin.protocol) || origin.username || origin.password || origin.pathname !== '/' || origin.search || origin.hash) {
    throw new TypeError('SEO origin must be an HTTP(S) origin without credentials, a path, query, or fragment');
  }
  const basePath = config.basePath ?? '/';
  if (typeof basePath !== 'string' || !/^\/(?:[A-Za-z0-9._~-]+\/)*$/.test(basePath) || basePath.split('/').some(segment => segment === '.' || segment === '..')) {
    throw new TypeError('SEO basePath must be / or slash-delimited path segments ending in /');
  }
  const siteUrl = `${origin.origin}${basePath}`;
  if (config.siteUrl != null && config.siteUrl !== siteUrl) {
    throw new TypeError('SEO siteUrl must equal origin plus basePath');
  }
  const hostname = origin.hostname.toLowerCase();
  const localHost = hostname === 'localhost' || hostname.endsWith('.localhost') ||
    hostname === '127.0.0.1' || hostname === '[::1]' || hostname === '0.0.0.0';
  // An explicit production flag still cannot turn a local HTTP preview into an
  // indexable release. Build configuration is responsible for the final domain.
  const production = config.production === true && origin.protocol === 'https:' && !localHost;
  return {
    name: config.name || 'Mixer',
    title: config.title || 'Mixer — Swift in. Native out.',
    description: config.description || 'Build native iOS and Android apps with shared Swift. Ship with local and managed builds, signed compatible updates, staged rollouts, and recovery.',
    basePath, siteUrl, production,
    absolute: path => new URL(path.replace(/^\//, ''), siteUrl).href
  };
}

function pagePath(pathname) {
  // The build passes a route relative to basePath; queries never belong in
  // canonical URLs. Unknown routes receive 404 metadata and cannot be indexed.
  const path = String(pathname ?? '/').split(/[?#]/, 1)[0];
  if (path === '/' || path === '/index.html') return '/';
  if (path === '/docs' || path === '/docs/index.html') return '/docs/';
  if (path === '/privacy' || path === '/privacy/index.html') return '/privacy/';
  return Object.hasOwn(PAGE_DETAILS, path) ? path : '/404.html';
}

function structuredData(options, pathname, page) {
  const { name, siteUrl, absolute, description } = options;
  const organizationId = `${siteUrl}#organization`;
  const websiteId = `${siteUrl}#website`;
  const softwareId = `${siteUrl}#software`;
  const graph = [
    {
      '@type': 'Organization', '@id': organizationId,
      name, url: siteUrl,
      logo: {
        '@type': 'ImageObject', url: absolute('/assets/icon-512.png'),
        width: 512, height: 512
      }
    },
    {
      '@type': 'WebSite', '@id': websiteId, name, url: siteUrl,
      description, inLanguage: 'en-US', publisher: { '@id': organizationId }
    },
    {
      '@type': 'SoftwareApplication', '@id': softwareId, name,
      applicationCategory: 'DeveloperApplication', description, url: siteUrl,
      image: absolute('/assets/og-mixer.png'), publisher: { '@id': organizationId }
    },
    {
      '@type': pathname === '/docs/' ? 'TechArticle' : 'WebPage',
      '@id': `${absolute(pathname)}#page`, url: absolute(pathname),
      name: page.title, description: page.description,
      isPartOf: { '@id': websiteId }, about: { '@id': softwareId },
      inLanguage: 'en-US'
    }
  ];
  if (pathname === '/docs/') {
    graph.push({
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name, item: siteUrl },
        { '@type': 'ListItem', position: 2, name: 'Documentation', item: absolute('/docs/') }
      ]
    });
  }
  return { '@context': 'https://schema.org', '@graph': graph };
}

export function createSeoHead({ pathname = '/', config }) {
  const options = settings(config);
  const path = pagePath(pathname);
  const page = path === '/' ? { title: options.title, description: options.description } : PAGE_DETAILS[path];
  const is404 = path === '/404.html';
  const indexable = options.production && !is404;
  const meta = (name, content) => `<meta name="${escapeHtml(name)}" content="${escapeHtml(content)}">`;
  const property = (name, content) => `<meta property="${escapeHtml(name)}" content="${escapeHtml(content)}">`;
  const link = (rel, path, extra = '') => `<link rel="${rel}" href="${escapeHtml(options.absolute(path))}"${extra}>`;
  const lines = [
    `<title>${escapeHtml(page.title)}</title>`,
    meta('description', page.description),
    meta('robots', indexable ? 'index, follow, max-image-preview:large' : 'noindex, nofollow'),
    meta('theme-color', '#f8f7f4'),
    meta('color-scheme', 'light'),
    property('og:type', 'website'),
    property('og:site_name', options.name),
    property('og:locale', 'en_US'),
    property('og:title', page.title),
    property('og:description', page.description),
    property('og:image', options.absolute('/assets/og-mixer.png')),
    property('og:image:type', 'image/png'),
    property('og:image:width', '1200'),
    property('og:image:height', '630'),
    property('og:image:alt', IMAGE_ALT),
    meta('twitter:card', 'summary_large_image'),
    meta('twitter:title', page.title),
    meta('twitter:description', page.description),
    meta('twitter:image', options.absolute('/assets/og-mixer.png')),
    meta('twitter:image:alt', IMAGE_ALT),
    link('icon', '/assets/favicon-32.png', ' type="image/png" sizes="32x32"'),
    link('apple-touch-icon', '/assets/apple-touch-icon.png', ' sizes="180x180"'),
    link('manifest', '/site.webmanifest')
  ];
  if (!is404) {
    lines.push(link('canonical', path), property('og:url', options.absolute(path)));
    lines.push(`<script type="application/ld+json">${serializeJson(structuredData(options, path, page))}</script>`);
  }
  return lines.join('\n');
}

export function createSearchFiles(config) {
  const options = settings(config);
  const urls = options.production ? INDEXABLE_PATHS.map(path =>
    `  <url><loc>${escapeHtml(options.absolute(path))}</loc></url>`).join('\n') : '';
  const robots = options.production
    ? `User-agent: *\nAllow: /\n\nSitemap: ${options.absolute('/sitemap.xml')}\n`
    : 'User-agent: *\nDisallow: /\n';
  const manifest = {
    id: options.basePath,
    name: options.name,
    short_name: options.name,
    description: options.description,
    lang: 'en-US',
    start_url: options.basePath,
    scope: options.basePath,
    display: 'standalone',
    background_color: '#f8f7f4',
    theme_color: '#f8f7f4',
    icons: [192, 512].map(size => ({
      src: `${options.basePath}assets/icon-${size}.png`,
      sizes: `${size}x${size}`, type: 'image/png', purpose: 'any'
    }))
  };
  return {
    'robots.txt': robots,
    'sitemap.xml': `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}${urls ? '\n' : ''}</urlset>\n`,
    'site.webmanifest': `${JSON.stringify(manifest, null, 2)}\n`,
    'humans.txt': 'Mixer\nSwift in. Native out.\n\nAn independently authored Swift-first mobile development platform.\nWebsite: original static HTML, CSS, and JavaScript.\nMascot: Flick, the Mixer fox.\n',
    'llms.txt': `# ${options.name}\n\n> A Swift-first developer platform for native iOS and Android apps.\n\nMixer combines shared Swift application code, MixerUI native platform adapters, local and managed builds, and a controlled workflow for signed compatible logic and UI updates. Compatibility depends on the installed native runtime and supported capabilities. Native capabilities, permissions, app icons, and store metadata follow the native build and store release path.\n\n## Pages\n\n- [Mixer](${options.siteUrl}): Product overview, workflow, and plans.\n- [Documentation](${options.absolute('/docs/')}): Getting started and release model.\n- [Website privacy](${options.absolute('/privacy/')}): Data handling on this website.\n\n## Scope\n\nMixer is developer tooling, not a consumer mobile app listing. FieldLog is a separate application built with Mixer. This file describes the product and is not evidence of App Store approval, performance results, security certification, customer adoption, or production qualification.\n`
  };
}
