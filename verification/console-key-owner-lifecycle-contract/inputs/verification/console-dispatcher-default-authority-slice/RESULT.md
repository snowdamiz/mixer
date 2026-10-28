# Private dispatcher default authority result

Candidate 6 passed its single root-released host execution in **3.998 seconds**.
The exact 36-source ordinary closure compiled 39 modules, and the standalone test
input compiled three modules, both with zero compile/runtime warnings. ExUnit
executed all seven methods: seven passed, zero failed, skipped or excluded.

The authoritative inputs and result are:

* `candidate-6/execution-plan.json`, SHA-256
  `b4b12f74a27914bfc8382ac0fdc11700a6aa8c34dd246e073ca4815fee90c138`.
* `candidate-6/execution/receipt.json` and its bound command/output files.
* `candidate-6/execution/default-authority-tests.stdout.txt`,
  `exunit-result.json`, `component-cleanup.json` and `postrun-observations.json`.
* Unchanged v5 test/bootstrap sources, copied under candidate 6's frozen inputs.

This qualifies the fixed private dispatcher with actual ordinary default
`BearerIdentity.init([])` / `ConfiguredVerifier.authenticate/2`, a registered
default KeyOwner using its existing local TLS refresh fixture, the ordinary
controller/facade and actual default `MixerHosted.Repo`. The runtime connection
was the same restricted current/session role, without superuser, RLS bypass,
database/role creation or owner membership. The complete explicit twelve-table
authority set had ENABLE/FORCE RLS and the intended nonlogin owner.

The seven passing methods establish default organization/project projection,
foreign/nonmember tenant denial, canonical database pagination and exact tenant
bytes, invalid-signature/audience/expired-token rejection, missing-scope denial,
same-token committed role/membership revocation, six current database identity
state controls including credential revocation/expiry, outside-context RLS/write
refusal, and inherited-transaction/dynamic-Repo refusal. Every successful dispatch
observed the canonical directory transaction's restricted role/context through
read-only telemetry. Exact public page/error keys, fixed messages and complete
headers exclude raw identity/private fields. The single-connection runtime pool
and caller were checked for all twenty authorization GUCs and inactive
transaction/Storage/Context state after success and denial.

Cleanup passed at both layers. The owner was alive, with refresh/TLS dependencies
alive, before an explicit normal stop through the existing KeyOwner terminate
path. Admission/default owner/default Repo were absent and all six components
stopped. TLS ephemeral key material was removed; at least one normal JWKS refresh
was observed. All eight direct OS children were reaped, all eight exact owned
process groups were absent, PostgreSQL and TLS ports were closed, the postmaster
pid file was absent and owned scratch was removed. All 1,003 original
source/tool/dependency pins remained unchanged, with no input-read errors.

Observed tools were Elixir 1.20.4 / Erlang OTP 29 (pinned OTP 29.1.1), Python
3.14.8, PostgreSQL 17.11 Homebrew and LibreSSL 3.3.6. The source context was
`6f116c6a41994fcab5fa0d203198dc139dae9829`, with commit tree
`744e2c58845c52bee1038f1602827cdb8b95ae24`; the frozen working-input manifest and
per-file hashes bind the uncommitted verification additions. No canonical
product, workflow or metadata source was changed by this lane.

All earlier evidence remains preserved. Candidates 1 and 5 were superseded by
source review without runtime execution. Candidate 2 invalidated all seven tests
at migration pool setup and emitted one test-source warning; candidate 3 compiled
cleanly but invalidated all seven at the erroneous thirteen-table assertion.
Candidate 4 completed all seven method bodies but its suite failed teardown on
the stale Admission pointer, then lost framework JSON to a bootstrap assertion.
Each executed failure retains raw output, exact inputs and successful owned OS
cleanup. None is relabeled a pass.

This is a local host development slice with synthetic RS256/JWKS identity and
disposable loopback PostgreSQL without database TLS. It does not qualify
production provider/public DNS, owner supervision/startup/shutdown or custody,
callback/session/cookie authority, Endpoint/Router/HTTP/browser integration,
transaction-race/commit-fault matrices, PostgreSQL 16 CI, Neon/Cloudflare,
customer workflows, published-package FieldLog, W14/G22 or GA. Computer use,
capture and native simulator/emulator runtime remain paused; physical phones
remain disconnected and final native acceptance remains pending. Root owns
canonical acceptance, metadata and delivery.
