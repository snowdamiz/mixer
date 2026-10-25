# Mixer console release-check view

The first SolidJS console view uses the existing website's Flick logo, lowercase
wordmark, effective cream-and-orange palette, typography, and favicon. The
website remains the branding source of truth. The console adds a responsive
workspace shell, readable per-platform result tables, and clear release states;
the product plan now explicitly requires this identity throughout the hosted
builds platform, with Expo as a quality reference.

`/releases` currently shows that no release data source is connected. In
development, `/preview/release-checks` exercises failure, incomplete/stale,
passed, loading, unavailable, and invalid-data states using labeled synthetic
data. Production excludes that data and returns not-found for the preview
route. Missing, unrun, and previous-revision results cannot become a pass;
current failures remain visible. This component displays evidence and grants
no release authority.

Validation: 17 repository tests pass (nine domain, seven compiled Solid view,
one website-brand parity), plus six independent compiled view tests. Strict
application typechecking and production builds pass. Browser checks cover all
six reactive states, production route exclusion, a working keyboard skip link,
and a 375-pixel layout with no horizontal overflow. The desktop and mobile
captures are retained in `verification/console-release-check-view/`.

The browser exposed an initial skip-link focus defect, corrected by bypassing
Solid Router's interception for the main-landmark anchor. An attempted native
select arrow-key change did not change its value; this behavior remains
unverified. Broader screen-reader and accessibility qualification is pending.
Dependency declarations use `skipLibCheck` for the independently reproduced
Router 1.0.0 `AnchorProps.replace` incompatibility with exact optional types;
owned application sources retain strict checking. Initial harness failures and
the superseded visual design are retained as historical evidence.

Run `npm ci --ignore-scripts --no-audit --no-fund`, `npm run typecheck`,
`npm test`, and `npm run build` from `console/`. Run
`python3 verification/console-release-check-view/audit.py` at the original
`67d6d045` checkout to verify its saved source/output bindings and browser
observations. On later revisions the historical audit also checks shared root
metadata and can reject unrelated provenance updates. The current-source review
in `verification/console-brand-current-review/receipt.json` records the later
`THIRD_PARTY.yml` change while confirming all console/website source, asset,
build-output and saved browser evidence bindings remained unchanged. Neither
check reruns the browser.

The exact versions, commands, source hashes, limitations, cleanup, and independent
review are linked from [the receipt](../verification/console-release-check-view/receipt.json).
All owned browser tabs and local servers were stopped after capture. No native
simulator, emulator, physical phone, deployment, or customer operation was used
for this slice. Phoenix data/auth integration, full hosted-build workflows,
Cloudflare hosting, G22, and other GA/dogfood gates remain pending.
