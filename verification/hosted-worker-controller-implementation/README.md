# Frozen per-operation controller slice

Scope: strict internal wire/principal, per-operation SQLite DO ledger, durable
intent/stop/claim, recovery and local alarm boundary. Complete controller/fleet
and operational acceptance are pending. Root explicitly deferred independent
audit registry/scheduler and missed-wake/exhausted-alarm retry recovery source.

The implementation is `hosted-worker-controller/`; the product/limitation report
is `docs/hosted-worker-controller-implementation.md`. The original contract and
transport packets remain unchanged. No live hosted module or shared status was
modified. This packet contains no cloud deployment/provider/account changes.

Final commands from `hosted-worker-controller/`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run build
npm test
node audit-build.mjs
```

Independent reviewers should set `MIXER_CONTROLLER_TEST_REPORT` to their own
absolute output path when replaying tests, preserving this packet's report.
That setting is test-runner-only and cannot configure production behavior.
Production qualified time/provider/object verification is unavailable by default;
real runner authentication and sandbox grants are absent, rather than faked.

From the repository root, `python3 verification/hosted-worker-controller-implementation/verify_snapshot.py`
checks the frozen source/dependency/artifact archive and recorded cleanup. It
does not accept application correctness or operational gates. `collect.py`
created the snapshot; rerunning it refreshes evidence and must not be used to
retarget old results silently.

The final suite reports 28 passing groups, including the unchanged frozen20
scenarios/five fixtures, original36 producer vectors, extra24 pinned-Jason
control/Unicode vectors, actual SQLite process restart/SIGKILL, concurrency,
claim, teardown and no-customer-HTTP alarm checks. Four SIGKILL cases identify
the exact owned workerd child. 114 cleanup records cover owned processes/storage.
The fake provider/object verifier is confined to an excluded verification bundle
and does not qualify actual provisioning, isolation, private objects or signing.

Numbered failed attempts are retained. The first build had type errors; the
first runtime smoke had a Miniflare ESM-rule error; `test-attempt-2` revealed a
real Jason uppercase-control-escape hash difference. The repair also matches
Elixir's DEL printable character. The approved Jason-only probe asserts zero
Mixer modules and seals exact BEAM bytes. Historical source trees were not
individually archived at failure; the final complete source tree is sealed.

`THIRD_PARTY.yml` inside the project covers all58 locked development package
entries with licenses/integrity/purpose. Both installation and clean reinstall
disabled scripts; no dependency install script ran. `dependency-files.json`
records every actual installed toolchain file. `source-snapshot.tar.gz` contains
the exact owned source/compiled output and necessary frozen contract/vector
inputs, rather than the large dependency binaries. Lockfile integrity and the
dependency manifest bind those binaries separately.
