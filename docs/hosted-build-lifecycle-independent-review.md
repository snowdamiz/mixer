# Hosted build lifecycle independent review

Verdict: the sealed deterministic, host-only lifecycle component passed independent
review. No unresolved actionable finding was reproduced in this scope. Root owns
integration and acceptance; this review does not pass W12, hosted operations,
G22, device, release, billing, or GA gates.

## Accepted source and execution

The reviewer waited for the producer's explicit final immutable handoff before
accepting or executing the snapshot. Every one of the handoff manifest's 21 file
entries matched both SHA-256 and byte count. The producer manifest SHA-256 is
`15f20b5a536876be48acdfa36d155b15b74b4b66c4fddbec9eb56846c6f4779e`.

The accepted source revision is
`ccd8e4c3d96f96876a1339a51dc4297f4175d4fc`. The implementation, producer test and
contract document were copied into
`verification/hosted-build-lifecycle-independent-review/accepted-source/`.
The implementation and producer test tree digest is
`c00622e2b2794ca647130a4cbf7622faffaccd4ad2c89e49f38daa50419e7aea`.

| Sealed input | SHA-256 |
| --- | --- |
| `hosted/lib/mixer_hosted/builds/lifecycle.ex` | `e203ffe0134be5278d9b66f0eb8dadc260d7ffb259d11135dcc4665feb1e72a9` |
| `hosted/test/mixer_hosted/builds/lifecycle_test.exs` | `6c286694447daa100fe487267b483a75b896109b95c1d8b10144f22d24c84881` |
| `docs/hosted-build-lifecycle.md` | `c58e55facde2e3586f555e712e55a21a1cbd01ffad02ad0c8b1736516aa091a6` |

The reviewer independently reran the producer suite against the copied source:
**21 passed, exit 0**. A separate independently authored hostile control suite
against that source produced **10 passed, exit 0**. Raw stdout/stderr, exact
arguments, timeout, elapsed time, tool output, host identity and input digests are
retained in `verification/hosted-build-lifecycle-independent-review/commands/`
and `results.json`. All producer handoff files and all snapshot/control inputs
were unchanged during execution.

The environment was Darwin arm64, `/opt/homebrew/bin/elixir` 1.20.4 and Erlang/OTP
29.1.1. Every Elixir command used `ERL_FLAGS='+S 2:2'`; each test process had a
120-second limit. These were standalone `elixir -r ... -e ...` executions. No Mix,
test helper, application startup, database, network, provider, native harness, or
frozen authority lane was invoked. No simulator, emulator, phone, container or
persistent service was created, and no other project's processes were changed.

## Independent controls

| Control | Observed result |
| --- | --- |
| Change each organization/project/application/build/platform/attempt/fence field | 77 wrong-reference combinations reject start, completion, stop or expiry; another scope's numerically equal attempt/fence cannot match. |
| Replay every accepted event after a successful retry | Exact event ID plus payload returns the unchanged latest state even when the new delivery time is nil, negative, above signed64, or far later; first observation times remain unchanged. Changed payload conflicts. |
| Fill a trusted synthetic event ledger to 32 | Fresh otherwise-valid completion rejects with `event_limit`; exact duplicate and conflicting duplicate remain readable. A 33-entry trusted synthetic state rejects as invalid. |
| Cancellation, expiry, expiry then cancellation | Old active identity remains present and customer status stays pending; elapsed time, retry, start, or an invented newer fence cannot authorize replacement. Only the original matching terminal observation closes uncertainty. Late success references are discarded. |
| Known compiler/test/policy/unknown failures across deadlines | All five allowed noninfrastructure class/code pairs remain nonretryable before, exactly at, and after deadline, including an already expired/reconciling worker: 20 combinations. |
| Infrastructure retry allowlist | All five allowed infrastructure codes obey backoff and attempt exhaustion; four unsupported or mismatched class/code pairs reject. |
| Five attempts with expiry and definitive stop | Both the 19-event exhausted-timeout path and 20-event final-cancellation path retain ordered five-attempt history. Every accepted historical event can be replayed without reopening or replacing the final state. |
| Signed64 limits | Valid maximum deadline is retained; overflowed deadline, backoff or synthetic fence cannot wrap. A definitive terminal observation survives backoff overflow while retry stays blocked. |
| Seven typed immutable output roles | Identical digest and size may serve distinct required roles. Conflicting size, duplicate/missing role, mutable URL field, untyped maps, wrong count, improper list and out-of-range byte counts reject. Successful outputs cannot be replaced. |
| Platform-specific customer projection | Android compiler failure remains failed beside successful iOS; projection invents no aggregate success, signing/release/billing decision, queue position or wait estimate. |

The 32-entry ledger and maximum-fence controls deliberately fabricate trusted
in-memory `Build` values: valid ordinary execution is bounded to 20 accepted
events and cannot reach the maximum fence. These controls exercise explicit
boundedness and overflow behavior. They do not establish untrusted hydration
validation. `valid_build?` performs shape checks on trusted application state;
it supplies no caller authorization, authenticated worker identity, durable CAS,
or distributed lease/lock.

## Findings and corrections

During pre-seal inspection, the producer reported and corrected a boundary where
a known nonretryable failure arriving after the deadline could be rewritten as
infrastructure timeout and become retryable. Independent controls above verify
both direct late terminal reporting and expiry reconciliation on the sealed
correction. The root-coordinated artifact contract was also finalized before
seal: shared digest is allowed across different roles only with identical size.
Both acceptance and conflict rejection passed independent controls.

No post-seal implementation correction was needed. The first review recorder
used an obsolete ExUnit summary pattern and queried `OTP_VERSION` from the
wrong runtime directory, so its initial summary correctly remained failed even
though both test processes exited zero. The original recorder and all outputs
remain under `attempts/initial-harness-version-and-summary-error/`. Metadata was
corrected from retained raw output, and a read-only version query confirmed
Elixir 1.20.4 / OTP 29.1.1. A first metadata-repair comparison also encountered
text-mode carriage-return normalization; the retained raw-byte comparison fixed
that recorder issue. No product test was rerun and no source/test was changed.
`metadata-repair-history.json` and `results.json` retain these facts and original
elapsed measurements.

## Product-plan credit and limits

This is narrow executable evidence toward sections 13.2, 14 and 17: explicit
scoped reconciliation references, uncertainty-preserving lifecycle decisions,
bounded retry policy, immutable typed artifact reference data and accurate
per-platform status. It makes no claim that supplied classifications or
references prove the truth of an external event.

The following remain separate, pending integration and operational evidence:
HTTP/tenant/worker authentication and authorization; durable request/event
uniqueness and serialized CAS; Ecto.Multi/Oban atomic commit; dispatch, actual
worker termination and orphan rescue; fleet quotas/capacity; hostile-code
isolation and worker teardown; source/toolchain/dependency resolution; artifact
existence, byte/content/provenance checks and private storage access; signing,
stores, release authority, charging and billing reconciliation. This host-only
review supplies no native or physical-device receipt and no customer or public
publication authorization.

The independent review manifest and its SHA-256 cover this document and the
owned review evidence. Root may accept the pure component independently of the
remaining integration/operational gates.
