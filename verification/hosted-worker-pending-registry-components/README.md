# Pending registry/audit component handoff

The candidate is isolated and ready for root review/integration. See
[the implementation note](../../docs/hosted-worker-pending-registry-components.md)
for behavior, source boundaries, the selected completion amendment and remaining
engine/deployed gates.

- `latest-run.json` selects the fresh source-bound passing run.
- `runs/20261025T042823425Z/receipt.json` records 17 workerd/SQLite groups plus
  20 process identity controls, exact tool versions, command EOF/group absence
  and all owned PID/storage cleanup.
- `candidate/src/` is the tested production component candidate. Its exact sealed
  public type copy is unchanged. The production AST closure has four modules/
  assets and only `cloudflare:workers` as an external import.
- `integration.patch` adds the five new source/type/SQL files only. Reuse the
  existing live `src/sql.d.ts`; candidate `assets.d.ts` supports isolated builds.
  Live build/engine/entry/test integration is root-owned and pending.
- `candidate/check.mjs` reproduces component build, process controls and runtime
  tests with existing pinned dependencies. `verify_components.mjs` verifies the
  current/frozen source hashes, compiled closure and packet integrity.
- `acceptance-coverage.json` maps all 30 selected cases. Full acceptance cases
  claimed passed: zero. Actual engine/pre-registration/outbox/barriers/recovery/
  migration/stop integration remains required.
- `failures/`, `historical/` and earlier `runs/` retain observed failures and the
  pre-completion 14-group evidence. They are superseded by the selected fresh run.

No cloud/native/UI/provider/auth/deployment action was taken. No live controller,
root tracker, package or Git state was edited by this lane. Parent coordinates
integration, existing 71 controller-group regression, commit and push.
