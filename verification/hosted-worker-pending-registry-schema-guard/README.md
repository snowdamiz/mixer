# Focused schema guard and terminal replay derivative

The production candidate changes only `pending-audit.ts` and `pending-registry.ts`.
Original producer/review packets and the eight-case schema receipt remain unchanged.

- `receipt.json`: combined handoff and distinct runtime source bindings.
- `latest-run.json`: final four-control terminal-replay run.
- `runs/20261025T044125775Z/receipt.json`: preserved eight-control schema run.
- `candidate/src/`: corrected sources; sealed public interface unchanged.
- `corrections.diff`: both selected deltas against original candidate source.
- `guard.diff` and `terminal-replay.diff`: separate source changes.
- `verify_packet.mjs`: current/archived source, original packet and closure checks.

Run `node verification/hosted-worker-pending-registry-schema-guard/run-check.mjs --terminal-only`
for the terminal controls. Omit the flag to run both focused suites. Actual SQLite
partial-schema fault controls remain excluded test code. No live integration,
Engine/Ledger edit, Git action, new dependency, deployment or GA qualification.
