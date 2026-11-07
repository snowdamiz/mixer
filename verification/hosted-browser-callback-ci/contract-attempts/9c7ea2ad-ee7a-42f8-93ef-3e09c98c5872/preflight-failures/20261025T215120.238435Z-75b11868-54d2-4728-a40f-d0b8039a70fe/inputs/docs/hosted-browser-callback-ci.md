# Selected browser callback CI fixture

Run the bounded callback storage slice after the locked dependencies have been
prepared, without starting the full hosted application:

```sh
python3 -B hosted/test/mixer_hosted/browser_auth/run_callback_fixture.py \
  --pg-bin /usr/lib/postgresql/16/bin \
  --output /tmp/mixer-browser-callback-evidence
```

The runner supports prepared PostgreSQL 16 and 17 executables. Both arguments
are required. Each invocation creates a fresh timestamp/UUID attempt under the
dedicated output directory; it refuses traversal, symlink parents, repository
ancestors and Git metadata. Invalid executable paths fail before creating output
or scratch resources. It never overwrites the callback storage producer packet.

The explicit ordinary source closure is compiled projectlessly against only the
selected locked dependency ebins already present in `hosted/_build/test/lib`.
The compiler rejects warnings. The actual Mix formatter checks the two Unit A
product files and callback fixtures from an empty scratch project. No dependency
build, whole-application discovery, rewritten source, injected Repo, clock or
provider is involved. The runner never reads or loads the frozen catalog
inspector, authority driver or rejected WorkerV2 implementation.

`verification/hosted-browser-callback-ci/selected-methods.json` binds the exact
existing fixture bytes and ordered method names: 30 preauth, 30 begin-login and
35 callback checks. Every suite is mandatory; there is no case selector. Its
environment excludes inherited `CALLBACK_CASE`, database credentials, Elixir
paths and Mix overrides. A coordinated reviewed fixture change must update the
explicit registry and expected counts before it can pass this runner.

One disposable loopback PostgreSQL cluster hosts synthetic restricted roles and
the existing migration installer. The unchanged fixtures exercise actual
`CallbackDraft`, `Store`, `RuntimeOwner`, the default `KeyOwner` and fixed
`LifecycleRepo`, including pool size two and queue-disabled admission. Each suite
uses its own output subdirectory and must report complete owned BEAM cleanup.
The runner records every command, timeout, exit, stdout/stderr, versions, revision,
Git tree, input snapshot, source and selected dependency hashes before and after,
method results, failure and cleanup. Source/dependency changes make a run fail.

Cleanup targets only the scratch directory's recorded device/inode and the
cluster's exact data directory and postmaster identity. A command timeout kills
only that command's owned process group. On ordinary failure or interruption the
runner attempts immediate cluster shutdown, verifies `pg_ctl status` reports
nonrunning, and removes only its owned scratch after successful identity checks.
Uncertain cleanup remains a failed receipt with retained scratch for diagnosis.

The `hosted.yml` workflow runs this selected closure after its existing dependency
preparation and storage/migration checks, using PostgreSQL 16 on Ubuntu. The
existing workspace, storage, migration and broad remote hosted checks remain in
place. The callback evidence directory is included in the always-run artifact
upload. A local PostgreSQL 17 pass does not establish Linux CI success; that
requires the actual remote workflow result.

This is host evidence for Unit A only. Manual trusted synthetic localhost runtime
configuration bypasses production TLS/5432 constructor qualification. Provider
exchange, routes, HTTP facade, Unit B, publication, immutable external FieldLog
dogfood, physical devices and GA acceptance remain outside this fixture. Native
runtime tests, computer use and screen capture remain paused.
