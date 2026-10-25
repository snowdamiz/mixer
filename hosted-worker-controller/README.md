# Mixer internal worker controller

This directory owns a per-operation Worker/SQLite Durable Object implementation.
The production entry is `src/index.ts`. Valid authenticated v1 commands currently
return bound unavailable observations because production clock/provider support
is disabled. Phoenix retains tenant and business authority. No deployment is
included. See `../docs/hosted-worker-controller-implementation.md` for scope and
the pending operational gates.

Use the pinned Node/npm versions in `package.json`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
node audit-build.mjs
```

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
