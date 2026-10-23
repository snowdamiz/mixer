# Mixer website

A static website using Node.js 22 or newer. Source lives in `src/`; public assets live in `public/`. The build, tests, and preview use only Node built-ins; no install step or runtime service is required. The build produces `dist/`, which can be hosted by any static host. The optional artwork exporter uses the pinned development-only `sharp` package.

```sh
cd website
npm test
npm run dev
```

The preview listens only on `127.0.0.1:4173`. It watches source and public assets, rebuilds serially, and retains the last successful output if a build fails. Refresh the browser after a rebuild. Restart the server after changing build scripts or configuration. Set `PORT` to change the port. `npm start` serves an existing build without watching or rebuilding.

A normal build is private by default: it emits `noindex` metadata and a disallowing `robots.txt`. The local preview also sends a `noindex` HTTP header, including when it serves a production build.

```sh
npm run build
```

An indexable production build requires your explicit public HTTPS origin:

```sh
SITE_URL=https://your-owned-domain.com npm run build:production
```

Production rejects local and example hosts. `SITE_URL` contains only an origin; set `SITE_BASE_PATH=/mixer/` when hosting in a subdirectory. Internal navigation, metadata, search files, and assets respect the base path. Configure the host to serve directory indexes, return `404.html` with HTTP status 404 for missing paths, and enable HTTPS. Building does not deploy or publish anything.

Optional environment variables:

| Variable | Meaning |
| --- | --- |
| `SITE_URL` | Public origin; defaults to `http://localhost:4173` for local builds. |
| `SITE_BASE_PATH` | Hosting path, such as `/mixer/`; defaults to `/`. |
| `SIGNUP_URL` | Primary action destination; defaults to `/docs/` under the base path. Root-relative paths use the base path; absolute HTTP(S) URLs are supported, with HTTPS required in production. |
| `REPO_URL` | HTTPS repository URL; defaults to `https://github.com/snowdamiz/mixer`. |
| `PORT` | Local preview port; defaults to `4173`. |

HTML source uses `{{SEO_HEAD}}`, `{{BASE}}`, `{{YEAR}}`, `{{SIGNUP_URL}}`, and `{{REPO_URL}}`. The build replaces URL tokens with HTML escaping and provides per-page metadata through `scripts/seo.mjs`. `createSeoHead({ pathname, config })` receives an unmounted route such as `/docs/`; `createSearchFiles(config)` returns generated filename-to-text entries. Public assets copy byte for byte. Source/public name collisions, symlinks, missing required source pages, unresolved placeholders, and unsafe generated filenames fail the build.

Tests exercise configuration, complete output generation, and actual HTTP requests for directory routes, MIME types, missing pages, HTTP methods, and traversal/symlink containment. Host website checks do not qualify mobile runtime, physical devices, app stores, published SDK packages, customer adoption, or production operations.

## Brand and marketing assets

Flick is the user-selected fox from concept 13. `public/assets/flick.png` is the transparent raster master; `marketing/flick-approved-concept.png` preserves the selection. The built-in image-generation edit prompt is retained in `marketing/flick-production-prompt.txt`. No editable vector master is claimed. The site uses responsive WebP exports, with reserved image dimensions and lazy loading below the first screen.

To rebuild raster exports, install the pinned optional tooling and run:

```sh
npm ci
npm run assets
```

Alternatively point `SHARP_MODULE_PATH` to an existing compatible sharp installation. The exporter uses the checked-in master, creates favicons, touch/browser icons, a 1200×630 Open Graph image, 1024×1024 store-sized brand art, a 1024×500 campaign graphic, and the downloadable brand ZIP. `marketing/assets/*.svg` are editable social-layout sources with the raster fox embedded; they are not vector mascot artwork.

`marketing/app-store.json` and `marketing/aso-guide.md` contain separate FieldLog listing copy, metadata limits, official source links, and screenshot capture briefs. Store-sized Mixer campaign artwork is a design asset; it is not an actual store listing or a FieldLog screenshot. Real store URLs, native screenshots, and store submission remain outside this website implementation.

## Interaction and publication scope

The light editorial design uses larger supporting type, soft card and device depth, and restrained pointer response in the hero. Pointer updates are coalesced through animation frames, run only for fine pointers, and stop when reduced motion is enabled. Reduced-motion changes also reveal any content waiting for a scroll transition. Mobile navigation remains available without JavaScript.

The release playground is a browser-local simulation labeled as an example. It sends no updates or account data. Tabs support arrow/Home/End keys; the mobile menu supports Escape; reduced-motion preference removes movement. CTA links default to the included source-install guide until a real console/signup destination is configured.

No domain was provided, so the delivered preview remains private-by-default and non-indexable. No production deployment, native app release, customer proof, or GA gate is claimed. Future-product copy follows the requested completed-product positioning; the repository's engineering status remains separately tracked in STATUS.md and gates/.
