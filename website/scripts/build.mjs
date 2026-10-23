import { cp, mkdir, readFile, readdir, rename, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { getConfig } from '../site.config.mjs';

export const websiteRoot = fileURLToPath(new URL('../', import.meta.url));
const textExtensions = new Set(['.html', '.css', '.js']);

function htmlEscape(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));
}

function tokenValue(value, extension) {
  if (extension === '.html') return htmlEscape(value);
  if (extension === '.js') return JSON.stringify(String(value)).slice(1, -1).replace(/'/g, '\\u0027').replace(/</g, '\\u003c');
  return String(value);
}

async function entriesUnder(directory, relative = '') {
  const result = [];
  for (const entry of await readdir(path.join(directory, relative), { withFileTypes: true })) {
    const name = path.join(relative, entry.name);
    if (entry.isSymbolicLink()) throw new Error(`Symbolic links are not accepted in website input: ${name}`);
    if (entry.isDirectory()) result.push(...await entriesUnder(directory, name));
    else if (entry.isFile()) result.push(name);
    else throw new Error(`Unsupported website input: ${name}`);
  }
  return result.sort();
}

function pagePath(filename) {
  const posix = filename.split(path.sep).join('/');
  if (posix === 'index.html') return '/';
  if (posix.endsWith('/index.html')) return `/${posix.slice(0, -'index.html'.length)}`;
  return `/${posix}`;
}

function ensureContained(directory, filename) {
  if (!filename || path.isAbsolute(filename) || filename.includes('\\') || filename.split('/').some((part) => !part || part === '.' || part === '..')) throw new Error(`Unsafe generated filename: ${filename}`);
  const absolute = path.resolve(directory, filename);
  if (!absolute.startsWith(`${path.resolve(directory)}${path.sep}`)) throw new Error(`Unsafe generated filename: ${filename}`);
  return absolute;
}

export async function buildSite({ config = getConfig(), srcDir = path.join(websiteRoot, 'src'), publicDir = path.join(websiteRoot, 'public'), distDir = path.join(websiteRoot, 'dist') } = {}) {
  const { createSeoHead, createSearchFiles } = await import('./seo.mjs');
  const sourceFiles = await entriesUnder(srcDir);
  for (const required of ['index.html', 'docs/index.html', 'privacy/index.html', '404.html', 'styles.css', 'app.js', 'docs.css']) {
    if (!sourceFiles.includes(required.split('/').join(path.sep))) throw new Error(`Missing website source: ${required}`);
  }
  let publicFiles = [];
  try {
    publicFiles = await entriesUnder(publicDir);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  for (const file of publicFiles) {
    if (sourceFiles.includes(file)) throw new Error(`Source and public files collide: ${file}`);
  }
  const searchFiles = createSearchFiles(config);
  for (const [filename, contents] of Object.entries(searchFiles)) {
    ensureContained(distDir, filename);
    if (typeof contents !== 'string') throw new Error(`Generated file must contain text: ${filename}`);
    if (sourceFiles.includes(filename) || publicFiles.includes(filename)) throw new Error(`Generated website file collides with input: ${filename}`);
  }
  const temporary = `${distDir}.building-${process.pid}-${Date.now()}`;
  await mkdir(temporary, { recursive: true });
  try {
    await cp(srcDir, temporary, { recursive: true, force: true });
    if (publicFiles.length) await cp(publicDir, temporary, { recursive: true, force: true });
    for (const filename of sourceFiles) {
      const extension = path.extname(filename);
      if (!textExtensions.has(extension)) continue;
      const location = path.join(temporary, filename);
      let contents = await readFile(location, 'utf8');
      const values = { BASE: config.basePath, YEAR: String(new Date().getUTCFullYear()), SIGNUP_URL: config.signupUrl, REPO_URL: config.repoUrl };
      for (const [token, value] of Object.entries(values)) contents = contents.replaceAll(`{{${token}}}`, tokenValue(value, extension));
      if (extension === '.html') {
        if (!contents.includes('{{SEO_HEAD}}')) throw new Error(`HTML page is missing {{SEO_HEAD}}: ${filename}`);
        contents = contents.replaceAll('{{SEO_HEAD}}', createSeoHead({ pathname: pagePath(filename), config }));
      }
      if (/\{\{[A-Z_]+\}\}/.test(contents)) throw new Error(`Unresolved template token in ${filename}`);
      await writeFile(location, contents);
    }
    for (const [filename, contents] of Object.entries(searchFiles)) {
      const destination = ensureContained(temporary, filename);
      await mkdir(path.dirname(destination), { recursive: true });
      await writeFile(destination, contents);
    }
    // Preparation finishes before the old output is replaced, so errors preserve the last working preview.
    await rm(distDir, { recursive: true, force: true });
    await rename(temporary, distDir);
  } catch (error) {
    await rm(temporary, { recursive: true, force: true });
    throw error;
  }
  return { distDir, config, files: [...sourceFiles, ...publicFiles, ...Object.keys(searchFiles)].sort() };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const unexpected = process.argv.slice(2).filter((argument) => argument !== '--production');
    if (unexpected.length) throw new Error(`Unknown build option: ${unexpected.join(', ')}`);
    const result = await buildSite({ config: getConfig(process.env, { production: process.argv.includes('--production') }) });
    console.log(`Built ${result.files.length} files at ${result.distDir}`);
    console.log(`${result.config.production ? 'Production, indexable' : 'Local preview, noindex'}: ${result.config.siteUrl}`);
  } catch (error) {
    console.error(`Website build failed: ${error.message}`);
    process.exitCode = 1;
  }
}
