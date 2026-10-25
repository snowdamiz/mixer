import { pathToFileURL } from 'node:url';
import { join } from 'node:path';
const { build } = await import(pathToFileURL(join(process.env.MIXER_REVIEW_DEPENDENCIES, 'vite/dist/node/index.js')));
await build({ root: process.env.MIXER_REVIEW_CONSOLE, logLevel: 'error', ssr: { noExternal: ['@solidjs/router'] },
  build: { ssr: process.env.MIXER_REVIEW_ENTRY, outDir: process.env.MIXER_REVIEW_SSR_OUT, emptyOutDir: false, minify: false } });
