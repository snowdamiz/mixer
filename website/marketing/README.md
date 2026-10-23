# Mixer discovery assets

The website presents the completed product positioning requested for Mixer. This directory is editable marketing collateral; it is not an implementation receipt, a store submission, or authorization to publish. `mixer-product-plan.md` remains the product scope and `gates/` remains the release evidence source.

`app-store.json` contains English (US) text and a six-screen capture story for **FieldLog**, the separate team-work application in plan section 21. Mixer is a developer platform and has no consumer store listing asserted here. Null publication fields are intentional. Replace them only with reviewed, working destinations for the actual application. Website mockups and generated marketing artwork do not qualify as app-store screenshots.

`aso-guide.md` records official requirements checked on October 23, 2026, capture guidance, and publication prerequisites. Metadata-length tests run with the website's Node test suite. No external dependency was added for discovery metadata or ASO collateral.

## Technical SEO

`scripts/seo.mjs` generates page-specific titles and descriptions, absolute canonical URLs, Open Graph and Twitter cards, native-size image hints, favicons, JSON-LD, a sitemap, robots rules, a web manifest, `humans.txt`, and `llms.txt`. JSON-LD describes Mixer as developer software without invented reviews, store IDs, pricing offers, or customer metrics. No `meta keywords` tag or fake social account is emitted.

Local/preview builds use `noindex, nofollow`, disallow crawling, and emit an empty sitemap. Production indexing requires an explicit production build and a configured HTTPS origin. Configure the actual site origin before deployment; this package does not guess a product domain. Production indexes the home page, documentation, and website privacy page. Missing pages have no canonical or JSON-LD and remain `noindex`.

All asset and page URLs preserve the configured base path. When deployed under a path prefix, the hosting operator must serve the generated `robots.txt` at the **origin root**; crawlers do not use a robots file under the prefix. Its sitemap URL already includes that prefix. Serve `/404.html` (or the configured prefix equivalent) with an actual HTTP 404 status for unknown routes, rather than returning the home page with status 200.

Before launch, set the canonical HTTPS origin, configure the real signup destination, confirm the legal owner and privacy/support details, verify hosting status codes and headers, and submit the generated sitemap through verified search-engine properties. A build check validates generated files; live indexing, social crawler fetches, and search rankings require a deployed site and are not claimed here. The manifest permits browser installation of the website; it does not declare a native iOS/Android application or offline capability.

## Social assets

Head metadata expects `assets/og-mixer.png` at 1200 × 630 pixels, `assets/favicon-32.png` at 32 × 32, `assets/apple-touch-icon.png` at 180 × 180, and manifest icons `assets/icon-192.png` and `assets/icon-512.png`. Keep the social image's text and Flick within a central safe region for cropping. Validate the final image and alt text together after changing campaign copy.

Optional campaign assets can live in this directory without being published as pages. `app-store.json` and the ASO guide are source collateral; they are not included in the website sitemap.
