# Mixer internal worker controller

This directory owns a per-operation Worker/SQLite Durable Object implementation.
The production entry is `src/index.ts`. Valid authenticated v1 commands currently
return bound unavailable observations because production clock/provider support
is disabled. Phoenix retains tenant and business authority. No deployment is
included. The V2 implementation fences the final claim against current authority,
persists accepted clock history, and quarantines existing schema-1 operations
while preserving permanent stops and consumed claims. See
`../docs/hosted-worker-controller-v2.md` for the reviewed candidate and
`../docs/hosted-worker-controller-v2-integration.md` for integration evidence.

Use the pinned Node/npm versions in `package.json`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
```

`npm test` rebuilds the controller, runs the original 28 groups, seven unchanged
review regressions and 36 focused repair groups, then checks the production import
closure. It prints a fresh evidence directory containing source hashes, tool
versions, command outputs and cleanup records. Set `MIXER_CONTROLLER_CHECK_DIR`
to a new directory to choose the destination. It never overwrites historical
verification receipts. The same command runs in Worker controller CI on Linux.

Do not enable package scripts globally. The workerd loader uses its pinned
optional platform binary without postinstall. `THIRD_PARTY.yml` inventories all
locked direct/transitive packages and licenses; `node inventory.mjs` reproduces it.

Tests use an excluded `test/worker.ts` bundle with finite synthetic clock/provider
behavior, actual workerd/SQLite persistence, and cleanup of owned processes and
storage. Never deploy that test bundle. The test harness cannot qualify a real
provider, hostile-code isolation, a trusted clock, runner credentials or R2 objects.
The production import-closure audit verifies test modules are unreachable from
the static deployment entry. Original and additional wire vectors live in the
repository verification packets; tests do not load the hosted Elixir application.
