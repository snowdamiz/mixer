# Independent browser migration wiring review

The reviewed migration wiring passes scoped independent host review. The five
ordinary fixture changes are limited to the ninth version/count and the latest
six rollback/reapply expectations; thirteen source checks cover these exact diffs,
selected CI invocation, PostgreSQL 16 arguments, evidence retention, default test
discovery exclusion and Python syntax. This does not execute the broad fixtures.

One independently authored real-PostgreSQL ExUnit method applies all nine
migrations, checks idempotence and exact schema_migrations rows, checks the
non-superuser/non-bypass owner, and tests actual restricted-runtime SQL denial
for SELECT, INSERT, UPDATE, DELETE, TRUNCATE and all nine public lifecycle calls.
It checks forced RLS and zero policies, deliberately grants PUBLIC execute and
disables RLS in this disposable database to detect both regressions, restores
inertness, and verifies latest-six rollback/reapply preserves exact build data.
Complete rollback leaves no browser relations/functions/types, and full reapply
restores inertness without creating or changing roles. Restricted-runtime checks
repeat across four phases (116 actual denied statements). The process/cluster
harness is a disclosed adaptation of the producer harness; the assertions are
independent and do not import the producer spec.

The final successful attempt is `attempts/20261025T160805.469882Z-359ce2ac/receipt.json`.
It records current source/dependency hashes, revision/tree digest, commands,
versions, complete output hashes and cleanup. StorageSchema has the frozen SHA-256
`676bb977bbe4c322caf63c1a5f40d86e7861847636029948b55cb01f6dedb6dd`.
Actual execution uses local PostgreSQL 17, Elixir 1.20.4 and OTP 29; PostgreSQL 16
CI is wired but remains pending. No Neon/deployment qualification is implied.
The first reviewer attempt failed because its own Repo pool size was one;
Ecto requires at least two for migrations. The corrected reviewer uses two.
That failed attempt is retained; no producer change was needed.

Every owned PostgreSQL instance was stopped and scratch removed, including the
failed run. No application, provider, browser/capture, native simulator/emulator
or phone was started. Frozen lanes and the broad hosted harness were not used.
Storage security correction review, runtime/provider/HTTP/console joining,
deployment/customer/browser/native and GA acceptance are separate requirements.
