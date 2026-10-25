# Browser storage CI fixture transaction alignment

The selected storage fixture now prepares its raw ordinary directory transaction
with `SET LOCAL jit = off` and verifies the effective value before installing
authorization context or reading organizations. This matches the already accepted
ordinary runtime policy in `Authorization.Postgres.Session`. The fix is confined
to `storage_spec.exs`; product Session, StorageSchema, shared StorageFixture,
migrations, discovery configuration and workflow commands are unchanged.
No SQL, lock, idle, test-runner or production limit is increased.

## Observed CI failure and local comparison

Phoenix run `40212854925` at source
`4492bbc74c47c77514951ae49b0fe418c7873db8` failed the selected storage
`setup_all` organization SELECT at the original `directory_rows/2` line 1319.
PostgreSQL returned `57014` after the existing five-second statement budget.
No test body executed: the result was **0 tests, 23 invalid**. The broad hosted
suite did not run afterward. The retained
[failure evidence](../verification/hosted-browser-storage-ci-fixture/ci-failure/receipt.json)
and [original selected output](../verification/hosted-browser-storage-ci-fixture/ci-failure/focused-exunit.log)
preserve that failure; it is not relabeled as a pass.

The [local baseline](../verification/hosted-browser-storage-ci-fixture/attempts/baseline-20261025T164833.502555Z-7750f0cc/receipt.json)
passes the original 23 selected methods without skips or exclusions. Its
`storage_spec.exs` SHA-256,
`dfffb543660d713a833b241f09d172e3576b0613051cd45e2657ceaa2bf706cc`,
equals the failed CI source manifest. The local CI timeout was **not reproduced**.
The baseline collector snapshots only its explicit selected sources and loads
hashed existing dependency BEAMs; no complete hosted app or frozen lane is loaded.

The same baseline attempt then recreates its two owned synthetic databases and
installs the same four migrations, grants, seed rows and ordinary authorization
context for a paired plan. The restricted login, backend PID, SQL and server
cost thresholds are the same for both observations; the only policy difference
is transaction-local JIT disablement. Statement/lock/idle bounds remain
`5s` / `500ms` / `5s` throughout. The inherited settings are restored after
both transactions.

| Local PG16 observation | Inherited JIT `on` | Transaction-local JIT `off` |
| --- | ---: | ---: |
| Estimated total cost | 107549.6 | 107549.6 |
| Actual execution time | 133.830 ms | 0.279 ms |
| JIT functions | 455 | No JIT node |
| JIT compilation time | 132.938 ms | No JIT node |
| End-to-end observed EXPLAIN call | 138.371 ms | 5.078 ms |

The [actual inherited plan](../verification/hosted-browser-storage-ci-fixture/attempts/baseline-20261025T164833.502555Z-7750f0cc/inherited-actual.json)
and [actual local-off plan](../verification/hosted-browser-storage-ci-fixture/attempts/baseline-20261025T164833.502555Z-7750f0cc/local_off-actual.json)
record `EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT JSON)`. JIT's default
thresholds remain 100000 / 500000 / 500000; no artificial threshold change or
timeout increase forces this comparison. These are sequential local observations,
with inherited JIT observed first, rather than a general latency benchmark.
They establish avoidable compiler work and the fixture preparation mismatch;
they do **not** prove which phase consumed the failed Ubuntu CI budget.

## Corrected selected execution

The helper snapshots backend PID, inherited JIT and all three existing bounds.
It uses only `SET LOCAL`, checks JIT is actually `off` without changing those
bounds, commits successful reads, rolls back SQL exceptions and checks the
original settings afterward. The new standalone test exercises inherited `on`
and `off` on the same owned restricted connection. For each prior state it
checks successful commit, a real invalid-integer RLS SQL error and rollback,
connection reuse, and exact settings restoration. The synthetic inherited-state
changes are restored before stopping that test connection.

The [final corrected attempt](../verification/hosted-browser-storage-ci-fixture/attempts/fixed-20261025T165255.300555Z-58012e3a/receipt.json)
passes **24 methods: the original 23 plus one new two-state restoration control**,
with zero failures, skips or exclusions. Its tested storage spec SHA-256 is
`bbb6f93902f743299e6c4189806757f3366ff20bcfed8fa56b0f9162d38e041c`;
the complete explicit input-tree digest is
`4215f52c76fc3157bfc67f1ec8232607a8976593a4b06fdbe9bbe293d8e05f7c`.
The three Postgrex disconnection logs in existing deferred-constraint controls
are expected audit/vault/attempt rejection cases, and all methods pass.

The [earlier corrected attempt](../verification/hosted-browser-storage-ci-fixture/attempts/fixed-20261025T165029.405149Z-dc474925/receipt.json)
also passes 24 methods against the same storage-spec bytes. The final repeat
checks the collector's corrected exit status, which now requires selected test
success as well as completed evidence collection.

All three attempts use one disposable pinned PostgreSQL 16.15 Debian Linux arm64
container at a time, Elixir 1.20.4 / OTP 29 with two schedulers on macOS, and
Python 3.14.8. They retain source snapshots and hashes, dependency hashes,
tool/image versions, exact commands and outputs. All owned containers are
stopped and removed, and scratch cleanup passes. Other projects' data and
processes are preserved.

Reproduce only the corrected selected suite from the repository root:

```sh
python3 verification/hosted-browser-storage-ci-fixture/run.py --label fixed
```

The historical baseline command was `--label baseline --plans`; its immutable
snapshot preserves the original source. The current source has 24 tests and is
not the original 23-test baseline. Exact-push Ubuntu Phoenix CI and its broad
hosted suite remain pending root delivery and review. No provider, browser,
native runtime, physical phone, production operation, FieldLog or GA gate is
qualified by these local checks. Computer use and native runtime checks remain
paused.
