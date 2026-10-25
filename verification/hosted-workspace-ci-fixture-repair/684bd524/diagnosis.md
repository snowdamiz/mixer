# 684bd524 Phoenix timeout and cold-read checkpoint

The exact-push Phoenix run
[40206421015](https://github.com/snowdamiz/mixer/actions/runs/40206421015)
is terminal **failure** for `684bd5246978767e290552d25773334103ffcf40`.
Its printed terminal result is **566/567 passed, 2 skipped**. The separate
`Browser auth protocol host checks` workflow step succeeded, from
15:21:54 to 15:21:59 UTC. That step result is distinct from the later failing
Phoenix/PostgreSQL step; counts must not be added across overlapping suites.

This is the same 5000ms transaction/checkout-exhaustion class as the earlier
`f2aba240` failure, but it occurs in a different case and SQL boundary. The first
workspace role/binding test fails its `orgs()` assertion at line 274. The timeout
stack is in `Storage.identity!/4` at line 347, called by the **post-lock** identity
check at line 85. It does not establish which preceding operation consumed the
transaction budget. The earlier large-customer case passes in 321.2ms and the
real membership-expiry lock case passes in 2838.4ms. The workspace fixture,
Storage, Session and authorization/workspace migration hashes match the earlier
failed CI receipt and the current checkout. CI uses PostgreSQL 16.15 on Ubuntu;
its PostgreSQL shutdown and scratch cleanup succeeded.

The artifact now has an `_temp/phoenix-foundation/` prefix and also contains
unrelated browser-auth receipt names. Only the exact prefixed `tests.log`,
`receipt.json` and `postgres-version.log` contents were read. Initial root-name
and ambiguous-basename lookups are recorded in the collection receipt. ZIP
metadata identified the permitted prefix; unrelated receipt contents and all
source archives remained unread. The ZIP was held in memory and not saved.

## Bounded local evidence

One owned PostgreSQL container was used at a time, using the recorded official
PostgreSQL 16.15 Debian image on Linux/arm64, UTF-8/C locale, the actual restricted
runtime login and production SQL/policies. The collector runs only the selected
ordinary workspace modules, 24 workspace methods and eight-migration controls.
Every transaction/statement bound remains 5000ms and the lock bound remains
500ms. No source from the shared broad harness or frozen lanes was executed.

The probe records each of the first organization transaction's 72 query events
and nonexecuting EXPLAIN plans for identity, topology and organization queries.
Ecto query measurements are captured before observer EXPLAIN calls.

| First organization read | Default JIT baseline | Valid transaction-local JIT-off diagnostic |
| --- | ---: | ---: |
| Organization query | 201.041ms | 5.886ms |
| Organization estimated plan cost | 107753.57 | 107753.57 |
| Organization JIT functions | 631 | No JIT node |
| Initial identity query | 1.108ms | 0.857ms |
| Post-lock identity query | 1.045ms | 0.689ms |
| Observed transaction through commit | 412.968ms | 121.005ms |
| Recorded EXPLAIN observer overhead | 86.643ms | 16.536ms |
| Diagnostic SET LOCAL and SHOW overhead | None | 0.879ms |

Observed transaction durations include the listed observer work plus unmeasured
telemetry/JSON/file I/O overhead. They are not uninstrumented production latency.
The organization query measurements themselves exclude the following observer
EXPLAIN. The approximately 34-fold local query reduction supports investigating a
transaction-local JIT policy; it **does not prove the cause** of the Ubuntu/amd64
CI exhaustion or establish its missing per-query timings.

Both accepted runs pass all 24 methods with zero failures, skipped or excluded
methods, and all eight-migration boundary controls. Those counts overlap. The
JIT-off intervention applies only to the observed first transaction; its owner
transaction reports `SHOW jit = off` and the organization EXPLAIN has no JIT
node. The original data, policies and pagination/expiry semantics remain intact.

`cold-read-jit-off-1` is retained as an **invalid intervention**. Its SET LOCAL
ran from BEGIN telemetry before the Repo transaction flag was established, so
the owning query still compiled 631 JIT functions. Its ordinary test pass is not
JIT-off acceptance. The assessment file records that limit. The corrected probe
injects after the completed local idle-timeout statement inside a confirmed
owner transaction and verifies the effective setting and plan.

All three attempts stopped their owned PostgreSQL container, removed the owned
container and removed scratch. Prior `f2aba240` evidence and historical repair
receipts remain unchanged. No product source was edited. No capture, UI/browser
automation, native runtime, phone, provider or deployment activity occurred.

## Proposal retained for resumption

The minimal policy to review is `SET LOCAL jit = off` after the existing local
time bounds and before topology work in the ordinary authorization transaction.
The exact directory-only versus shared Session placement remains a review
decision. It would retain all policies, privileges, data limits and deadlines;
no session-global setting or planner workaround is proposed.

Before accepting a product change, verify the actual restricted owner transaction
gets JIT off with the existing time bounds; verify the previous session JIT value
returns after commit and rollback; rerun the 24 workspace methods including
121-project pagination and actual expiry/locking; cover any affected ordinary
artifact/transaction consumers; and inspect the next exact-push Ubuntu CI result.
No such product change or additional experiment is selected in this checkpoint.

Work stops here at the user's requested pausing point. The automatic Phoenix run
remains failed, the CI timeout attribution remains open, and native/device,
provider and GA qualification remain pending.
