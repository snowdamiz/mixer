# Independent customer artifact facade review

The frozen `MixerHosted.CustomerArtifacts` application facade has no actionable
finding in this review. Twelve independent executable cases pass against its
actual authorization, signed admission, restricted PostgreSQL storage, staged
metadata read and audit implementations. This is a development-slice review, not
HTTP activation, deployment qualification or a GA gate.

The final evidence is
`verification/hosted-customer-artifact-facade-review/run-4/receipt.json`
(SHA-256 `398f484f3659fe4b2059da2eac483bfcd914cf13878f1226dde33bf5c0991681`).
Its input tree digest is
`a5541414b6c6a281d3d1a8937787550d5338c6175e4c62544caf6e7da631843a`.
The source revision is root-supplied context
`9662eda186e3beee084f92ac25c4116c92f2cebc`; this reviewer ran no Git command.
The source tree digest and individual input hashes identify the actual reviewed
uncommitted composition independently of that revision label.

## Frozen source and dependency scope

| File | SHA-256 |
| --- | --- |
| `hosted/lib/mixer_hosted/customer_artifacts.ex` | `8b099b45745c8705ab3f9da7216ea9ba011f1bfff7352eda1d5e76253a01a516` |
| `hosted/test/mixer_hosted/customer_artifacts_test.exs` (inspected, not executed by this collector) | `83eefefd88c7dc2efead13f9f138f011ac81032aaa63d670a4d8580f74f80c9d` |
| `docs/hosted-customer-artifact-facade.md` | `df55bd1c4c9811c95dbac5a294cc90d054e14dd761c250df68fd44ef87dea306` |
| `hosted/lib/mixer_hosted/customer_artifacts/postgres_storage.ex` | `b6e9fcd0c3df4f28b6da90589eb2d3c465780c4f8ec484ace74f893aeb216340` |
| `hosted/lib/mixer_hosted/customer_artifacts/schema.ex` | `5bd58744af4823374cc9a981b0699dc16c7d88f37bc8077a40b509cdf5426a19` |
| `hosted/lib/mixer_hosted/customer_artifacts/topology.ex` | `35b4cc8f6a91b9b5049dae2ae50d2c056f4066b5c4e88d2e4115d252c137f4cc` |
| `hosted/priv/repo/migrations/20261025000005_add_customer_artifact_storage.exs` | `a2ba075c48ca983dd9c7d32f0dac555c4a451ab9605cc473c63ec31db19fc7b6` |
| Independent `review_test.exs` | `0b6964cf55eb0741d920c560adc53858935deb1c51f4f044496a313b03f0811c` |
| Independent `run.py` | `ee18aea8329d9f1585c2347ae333aaa671956fb5f999121d1fea3e98d0e30590` |

The final collector combines the facade producer's `run-1/inputs` ordinary source
snapshot with the four explicitly coordinated storage files from storage
`run-12/inputs`. It verifies their producer receipt hashes before copying and
rejects other transitive dependency differences. Storage producer tree:
`1c28fcf24d648569e4e32ef7f40c3ab9aadf7e0bb0e056c2c673b834849fc20b`.
The schema repair and final topology prefix checks are therefore present in the
final facade run. Independent storage review, combined current-source CI and
migration smoke are separate evidence owned by their respective lanes/root.

The collector uses copied general-purpose dependency BEAMs in private scratch,
compiles selected copied ordinary sources with `elixirc --warnings-as-errors`,
and runs its own ExUnit file without shared Mix or a shared harness. Dependency
manifest digest:
`d750c4f0f2110c2d991d98110daafbcce855d4231df152cb49acfb6a2d9cb11d`.

## Review evidence

Source inspection confirms the public route accepts exactly organization and
project, while metadata accepts exactly reason and source IP. Repo, host, roots
and clock are selected only by the closed server application configuration.
Neither public request map selects a callback, actor, request ID, application or
environment. Upload validates the VerifiedIdentity shape and exact upload scope
before admitting signed envelope bytes. Read uses the real read scope at the
project metadata stage and resolves the actual signed application/environment
before exact authorization; the facade additionally compares configured target,
platform, runtime and digest. The trusted ingress obligation to supply source IP
cannot be established by this internal application API alone.

The independent tests exercise:

- Ephemeral Ed25519 signatures on synthetic Android `notes/review` and iOS
  `other-app/other-env` artifacts, preserving actual signed targets and retained
  bytes. No FieldLog/development fallback is installed or fabricated.
- Invalid/unwrapped/extended/expired identities and near-miss token scopes with
  a poison body, proving identity/scope rejection precedes body admission.
- Authority-field injection in every public route and metadata map, canonical
  IPv4/IPv6 handling, malformed UTF-8 and exact 512-byte reason/128-byte key bounds.
- Current configured app, environment, platform and runtime mismatch; corrupted
  signatures; foreign project; missing/malformed server configuration; revoked
  current trust roots; digest and audit-page boundaries.
- Fresh credential revocation on same-key retry/read/audit, changed-principal
  and changed-reason conflicts, unchanged source-IP retry behavior, and concurrent
  same-key uploads producing one artifact/event/key record.
- Real PostgreSQL deferred foreign-key COMMIT failure for upload, read and audit.
  A test-only trusted Ecto Repo `prepare_transaction/2` hook enqueues an invalid
  deferred FK insert after the complete authorization callback has returned its
  success value. Each public call returns `authorization_unavailable`; upload
  persists zero artifact/event/key rows. Read and audit expose neither their
  internally produced bytes/events nor a public success. Transaction/context
  bindings clear, and subsequent ordinary calls succeed. The three Postgrex FK
  disconnection logs are expected test evidence, not unexplained failures.

## Runs, environment and cleanup

| Run | Result | Scope |
| --- | --- | --- |
| `run-1` | Harness setup failed; zero tests, twelve invalid | Ecto required migration pool size at least two. The reviewer fixture used one. This was corrected only in the owned fixture; the failure is preserved. |
| `run-2` | 12 passed | Original producer storage/schema snapshot; only upload COMMIT injection. This run does not qualify repaired storage. |
| `run-3` | 12 passed | Repaired storage `run-12` snapshot; only upload COMMIT injection. |
| `run-4` | 12 passed | Final repaired storage `run-12` snapshot; upload, read and audit COMMIT injections. |

Reproduction:

```sh
python3 verification/hosted-customer-artifact-facade-review/run.py \
  --storage-snapshot verification/hosted-customer-artifact-storage/run-12
```

The collector records commands, outputs, dependency/source hashes and tool
versions in every receipt. The final environment is macOS arm64, Erlang/OTP 29,
Elixir 1.20.4, PostgreSQL 17.11 and Python 3.14.8. It creates a disposable local
loopback PostgreSQL cluster and synthetic `review_owner` NOLOGIN owner and
`review_runtime` login, with no superuser/bypass-RLS/create-role/create-database/
replication privileges on the runtime. Only the owned cluster is stopped, then
the private scratch directory and copied dependency BEAMs are removed. Every run
records `postgres_stopped: true` and `scratch_removed: true`. Other projects'
databases, processes, simulators and files were not manipulated.

No product source, producer evidence, shared graph/status/gate file or Git state
was edited. No provider/network service, native UI, screen capture, physical
device or publication was exercised. Identity records are explicit synthetic
post-verification fixtures; they do not establish provider authentication. The
COMMIT hook is a fault injector in the trusted test Repo and adds no public API.
Concurrent application-environment configuration replacement is not tested as an
atomic trust-rotation protocol; the implementation captures server configuration
per operation and rechecks its policy validity through owned effects. No claim is
made for R2/CDN delivery, separate-repository published-package FieldLog dogfood,
store/signing/native compatibility, operations or any accountable GA review.
