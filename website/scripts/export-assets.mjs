import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const require = createRequire(import.meta.url);
const sharp = require(process.env.SHARP_MODULE_PATH || 'sharp');
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const assets = path.join(root, 'public/assets');
const source = path.join(assets, 'flick.png');
const sourceBytes = await fs.readFile(source);
const fox = `data:image/png;base64,${sourceBytes.toString('base64')}`;
await fs.mkdir(path.join(root, 'marketing/assets'), { recursive: true });
for (const size of [128, 256, 512]) await sharp(source).resize(size, size).webp({ quality: 90, effort: 6 }).toFile(path.join(assets, `flick-${size}.webp`));
for (const size of [16, 32]) await sharp(source).resize(size, size).png().toFile(path.join(assets, `favicon-${size}.png`));
async function icon(size, name, ratio = .82) {
  const inset = Math.floor(size * ratio);
  const logo = await sharp(source).resize(inset, inset).png().toBuffer();
  await sharp({ create: { width: size, height: size, channels: 4, background: '#f8f7f4' } }).composite([{ input: logo, gravity: 'centre' }]).png({ compressionLevel: 9 }).toFile(path.join(assets, name));
}
await icon(180, 'apple-touch-icon.png');
await icon(192, 'icon-192.png');
await icon(512, 'icon-512.png');
await icon(512, 'icon-maskable-512.png', .65);
await icon(1024, 'app-icon-1024.png');
const icon32 = await fs.readFile(path.join(assets, 'favicon-32.png'));
const icoHeader = Buffer.alloc(22);
icoHeader.writeUInt16LE(1, 2); icoHeader.writeUInt16LE(1, 4);
icoHeader[6] = 32; icoHeader[7] = 32;
icoHeader.writeUInt16LE(1, 10); icoHeader.writeUInt16LE(32, 12);
icoHeader.writeUInt32LE(icon32.length, 14); icoHeader.writeUInt32LE(22, 18);
await fs.writeFile(path.join(assets, 'favicon.ico'), Buffer.concat([icoHeader, icon32]));
const social = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="630" viewBox="0 0 1200 630">
<rect width="1200" height="630" fill="#f8f7f4"/><path d="M74 542h1052" stroke="#dfdfd8"/>
<image x="70" y="56" width="61" height="61" xlink:href="${fox}"/><text x="138" y="99" font-family="Arial,Helvetica,sans-serif" font-size="41" font-weight="700" letter-spacing="-2" fill="#202524">mixer<tspan fill="#e56235">.</tspan></text>
<text x="78" y="239" font-family="Arial,Helvetica,sans-serif" font-size="88" font-weight="700" letter-spacing="-5" fill="#202524">Write Swift.</text>
<text x="76" y="342" font-family="Georgia,serif" font-size="99" font-style="italic" letter-spacing="-5" fill="#e56235">Ship both.</text>
<text x="82" y="406" font-family="Arial,Helvetica,sans-serif" font-size="25" fill="#69706c">One codebase. Native iOS and Android.</text>
<text x="82" y="445" font-family="Arial,Helvetica,sans-serif" font-size="25" fill="#69706c">Build, ship, and keep making it better.</text>
<ellipse cx="946" cy="281" rx="179" ry="191" fill="#f0ddcd"/><ellipse cx="946" cy="289" rx="211" ry="140" stroke="#dfc7b2" fill="none" transform="rotate(-25 946 289)"/>
<image x="768" y="100" width="359" height="359" xlink:href="${fox}"/>
<rect x="808" y="452" width="108" height="37" rx="18" fill="#fffdf8" stroke="#e0d9ce"/><text x="862" y="477" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#50594c">iOS</text>
<rect x="932" y="452" width="129" height="37" rx="18" fill="#fffdf8" stroke="#e0d9ce"/><text x="996" y="477" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#50594c">Android</text>
<text x="82" y="585" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#818a79">LOCAL-FIRST. NATIVE BY DESIGN. YOURS TO KEEP.</text><text x="1120" y="585" text-anchor="end" font-family="Arial,Helvetica,sans-serif" font-size="16" fill="#818a79">SWIFT IN. NATIVE OUT.</text></svg>`;
await fs.writeFile(path.join(root, 'marketing/assets/og-mixer.svg'), social);
await sharp(Buffer.from(social)).png({ compressionLevel: 9 }).toFile(path.join(assets, 'og-mixer.png'));
const feature = `<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1024" height="500"><rect width="1024" height="500" fill="#f8f7f4"/><text x="70" y="86" font-family="Arial,Helvetica,sans-serif" font-size="32" font-weight="700" letter-spacing="-1" fill="#202524">mixer<tspan fill="#e56235">.</tspan></text><text x="66" y="220" font-family="Arial,Helvetica,sans-serif" font-size="72" font-weight="700" letter-spacing="-4" fill="#202524">Write Swift.</text><text x="65" y="306" font-family="Georgia,serif" font-size="84" font-style="italic" letter-spacing="-4" fill="#e56235">Ship both.</text><text x="70" y="380" font-family="Arial,Helvetica,sans-serif" font-size="21" fill="#69706c">One codebase. Native iOS and Android.</text><circle cx="794" cy="247" r="165" fill="#f0ddcd"/><image x="627" y="80" width="335" height="335" xlink:href="${fox}"/></svg>`;
await fs.writeFile(path.join(root, 'marketing/assets/feature-graphic.svg'), feature);
await sharp(Buffer.from(feature)).removeAlpha().png({ compressionLevel: 9 }).toFile(path.join(root, 'marketing/assets/feature-graphic-1024x500.png'));
await fs.copyFile(path.join(assets, 'app-icon-1024.png'), path.join(root, 'marketing/assets/mixer-app-icon-1024.png'));
await fs.writeFile(path.join(assets, 'brand-readme.txt'), 'Mixer / Flick brand assets\nSelected concept: Flick, the fox with one folded ear.\nPrimary: #e56235 orange / #202524 ink / #f8f7f4 warm white.\nKeep the folded ear and original expression. Keep clear space around the silhouette.\nThe artwork is supplied as raster PNG/WebP; no vector master is claimed.\nWeb, social and store-sized artwork are design assets, not evidence of a store listing.\n');
const zip = path.join(assets, 'mixer-brand-kit.zip');
await fs.rm(zip, { force: true });
execFileSync('zip', ['-q', '-j', zip, ...['flick.png', 'flick-512.webp', 'og-mixer.png', 'app-icon-1024.png', 'icon-512.png', 'icon-maskable-512.png', 'favicon.ico', 'brand-readme.txt'].map(name => path.join(assets, name))]);
console.log(`Exported Flick variants, social card, store-sized artwork, icons and brand kit using sharp ${sharp.versions.sharp}.`);
