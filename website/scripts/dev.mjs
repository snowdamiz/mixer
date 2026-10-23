import { createServer } from 'node:http';
import { watch } from 'node:fs';
import { readFile, realpath, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getConfig, normalizeBasePath } from '../site.config.mjs';
import { buildSite, websiteRoot } from './build.mjs';

const mimeTypes = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8', '.xml': 'application/xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.avif': 'image/avif',
  '.gif': 'image/gif', '.ico': 'image/x-icon', '.woff': 'font/woff', '.woff2': 'font/woff2',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.pdf': 'application/pdf',
};

function within(root, location) {
  const relative = path.relative(root, location);
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative));
}

export async function createStaticServer({ distDir = path.join(websiteRoot, 'dist'), basePath = '/' } = {}) {
  const root = await realpath(distDir);
  const mount = normalizeBasePath(basePath);
  return createServer(async (request, response) => {
    response.setHeader('Cache-Control', 'no-store');
    response.setHeader('X-Content-Type-Options', 'nosniff');
    response.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
    response.setHeader('X-Frame-Options', 'DENY');
    response.setHeader('X-Robots-Tag', 'noindex, nofollow');
    response.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self' https:; frame-ancestors 'none'");
    const send = (status, contents, type = 'text/plain; charset=utf-8') => {
      response.writeHead(status, { 'Content-Type': type, 'Content-Length': Buffer.byteLength(contents) });
      response.end(request.method === 'HEAD' ? undefined : contents);
    };
    const sendFile = async (location, status) => {
      const resolved = await realpath(location);
      if (!within(root, resolved)) return send(403, 'Forbidden\n');
      const contents = await readFile(resolved);
      return send(status, contents, mimeTypes[path.extname(resolved).toLowerCase()] || 'application/octet-stream');
    };
    const notFound = async () => {
      try { return await sendFile(path.join(root, '404.html'), 404); }
      catch (error) {
        if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return send(404, 'Page not found\n');
        throw error;
      }
    };
    try {
      if (!['GET', 'HEAD'].includes(request.method)) {
        response.setHeader('Allow', 'GET, HEAD');
        return send(405, 'Method not allowed\n');
      }
      let pathname;
      try { pathname = decodeURIComponent((request.url || '/').split('?', 1)[0]); }
      catch { return send(400, 'Malformed URL\n'); }
      if (!pathname.startsWith('/') || pathname.includes('\\') || /[\u0000-\u001f\u007f]/.test(pathname)) return send(400, 'Malformed URL\n');
      if (pathname.split('/').some((segment) => segment === '.' || segment === '..')) return send(403, 'Forbidden\n');
      if (mount !== '/' && pathname === mount.slice(0, -1)) {
        response.writeHead(308, { Location: mount });
        return response.end();
      }
      if (!pathname.startsWith(mount)) return await notFound();
      let location = path.resolve(root, pathname.slice(mount.length));
      if (!within(root, location)) return send(403, 'Forbidden\n');
      let info;
      try { info = await stat(location); }
      catch (error) {
        if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return await notFound();
        throw error;
      }
      if (!within(root, await realpath(location))) return send(403, 'Forbidden\n');
      if (info.isDirectory()) {
        if (!pathname.endsWith('/')) {
          response.writeHead(308, { Location: `${encodeURI(pathname)}/` });
          return response.end();
        }
        location = path.join(location, 'index.html');
      } else if (!info.isFile()) return await notFound();
      try { return await sendFile(location, 200); }
      catch (error) {
        if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return await notFound();
        throw error;
      }
    } catch (error) {
      console.error(`Preview request failed: ${error.message}`);
      if (!response.headersSent) send(500, 'Preview server error\n');
      else response.destroy();
    }
  });
}

async function start() {
  const unexpected = process.argv.slice(2).filter((argument) => argument !== '--no-build');
  if (unexpected.length) throw new Error(`Unknown preview option: ${unexpected.join(', ')}`);
  const port = Number(process.env.PORT || 4173);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be an integer from 1 to 65535.');
  const config = getConfig({ ...process.env, SITE_URL: process.env.SITE_URL || `http://localhost:${port}` });
  const shouldBuild = !process.argv.includes('--no-build');
  if (shouldBuild) await buildSite({ config });
  let server;
  try { server = await createStaticServer({ basePath: config.basePath }); }
  catch (error) {
    if (error.code === 'ENOENT') throw new Error('No dist directory found. Run npm run build first, or use npm run dev.');
    throw error;
  }
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  console.log(`Mixer preview: http://127.0.0.1:${port}${config.basePath}`);
  console.log('Local server sends noindex headers. Press Ctrl+C to stop.');
  const watchers = [];
  let timer;
  let building = false;
  let buildAgain = false;
  const rebuild = async () => {
    if (building) { buildAgain = true; return; }
    building = true;
    do {
      buildAgain = false;
      try { await buildSite({ config }); console.log('Website rebuilt. Refresh the browser to see changes.'); }
      catch (error) { console.error(`Website rebuild failed; previous output retained: ${error.message}`); }
    } while (buildAgain);
    building = false;
  };
  if (shouldBuild) {
    for (const directory of ['src', 'public']) {
      try {
        watchers.push(watch(path.join(websiteRoot, directory), { recursive: true }, () => {
          clearTimeout(timer);
          timer = setTimeout(rebuild, 80);
        }));
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
    }
  }
  const stop = () => {
    clearTimeout(timer);
    for (const watcher of watchers) watcher.close();
    server.close(() => process.exit(0));
  };
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  start().catch((error) => {
    console.error(`Website preview failed: ${error.message}`);
    process.exitCode = 1;
  });
}
