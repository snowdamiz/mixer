**REQUEST CHANGES — one P2 blocker: ordinary token rotation permanently disables reconciliation.**

Reviewed candidate `/Users/andreyyurlov/.t3/worktrees/mixer/t3-efc61fb9`, base
`96f03ab65966a6374e958e780fa09a3eed814c0b`, tree
`6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0`. The four delivered paths and full patch
match `patch-manifest.json`; full patch SHA-256 is
`e0937f48f97f3c70264364285f77b07917daa9f478fdcba22193aec1d32b68d0`.
The original review, candidate report, runner, both result receipts and source
were inspected. All 139 candidate snapshot inputs still match the delivered
candidate. Only this new review directory was written.

**P2 — remove the permanent credential-count lockout.**

Exact blocking source is `cli/Sources/MixerBuild/StoreReconciliation.swift:211-216`,
especially line 216, together with the unconditional commit refusal at line 246.
The bound is declared at line 123. Every distinct nonempty token of at most 256
UTF-8 bytes consumes one slot *before* authentication or any observed reflection.
The seventeenth sets `redactionsExhausted = true`. Nothing clears it. All later
successful, safe responses fail with `store.redacted-response`, including requests
using an earlier token or a longer team token. The last observation survives but
can never progress. HTTP still runs; this is not a provider rejection.

For example, query the same processing build with 16 successive individual-key
JWTs, then supply the seventeenth when the provider reports VALID. The last
processing observation remains frozen and the command reports unresolved.
Repeated use of one token does not exhaust the history; neither do exclusively
longer tokens on a fresh record. Missing credentials do not add a fingerprint.
Invalid nonempty short credentials do, so even rejected attempts can permanently
poison subsequent valid reconciliation. The problem is a lifetime quota on one
build identity, not a temporary byte, concurrency or provider rate limit.

Apple documents ES256 JWTs, individual-key `sub=user` claims, optional scope,
periodic renewal, and generally a maximum 20-minute lifetime. Reuse until expiry
is permitted; renewal is normal. Certain named resources permit longer scoped
tokens, which does not establish a lifetime count quota for this status reader.
A compact individual payload with the required claims, a ten-character key ID,
and a 64-byte ES256 signature produces a **250-byte** JWT. A corresponding team
payload with a UUID issuer produces **293 bytes**. Thus the <=256 branch affects
legitimate individual-key tokens; claiming all Apple JWTs bypass it is incorrect.
These lengths are calculations and locally signed test fixtures, not live Apple
acceptance. [Apple: Generating Tokens for API Requests](https://developer.apple.com/documentation/appstoreconnectapi/generating-tokens-for-api-requests).
The official Markdown was freshly fetched without credentials, retained in
`apple-generating-tokens.md`, and hash-bound in `official-docs-receipt.json`.

This contradicts the selected repeated existing-build reconciliation workflow
and product-plan Section 15's rotation/progress requirements. Calling it a
“development limit,” and passing a test that expects lockout, does not authorize
the workflow change.

**Executable evidence and a review-harness failure.**

One compile/test attempt ran, exactly as bounded. It compiled successfully and
executed 17 test groups; 15 reported pass and two reported six issues. These are
**not** six product findings or a successful complete review suite.

The new `StoreR2IndependentReviewTests` and original
`StoreSubmissionReconciliationTests` were each serialized internally but ran
concurrently with the same file-private `ScriptedASC.script`. My harness error
caused the fresh successful-query JWT rotation probe to stop at its initial
success precondition (copied test line 399), before reaching saturation. The
original recognized-credential transition also reported five issues during that
overlap. The 17-JWT success-to-lockout probe is therefore **inconclusive**; it is
not claimed as an independently reproduced successful-rotation sequence. No
second compile/test attempt was made. A future authorized run should place the
additional methods in the original serialized suite, or use separate fixtures.
The wrapper's `expected-failure-command-completed` status only records command
exit handling; it is not the semantic verdict.

There is nevertheless executable evidence for the blocking behavior. After the
independent suite ended, the unchanged candidate test
`credentialHistorySaturationPreservesSafeProgressAndClosesAdmission()` ran and
passed in isolation from it (candidate test lines 196-212). Through the production
reader and store, it records a safe observation, recognizes 17 distinct subsequent
short tokens on 401 responses, then supplies a safe 200 response. That successful
read is rejected with `redactedResponse`, `observationUpdated` stays false and
the prior observation remains unchanged. Its passing result reproduces the
unacceptable permanent closure. The source resolves the exact seventeenth-token
threshold and shows that prior HTTP outcomes are irrelevant to slot consumption.

The token generator built all 17 fixtures, locally checked their ES256 signatures,
and passed its 250-byte length/uniqueness expectations before the failed success
precondition. The separate small Python length control agrees. These establish
input size, not provider-account validation. The source plus the isolated
saturation control are sufficient to resolve the reported defect without another
attempt.

The other 11 candidate groups after the overlapping first group also passed,
including the original eight unchanged groups. Added migration, repeated-token,
long-token and cross-process controls printed passing results while the first
candidate group was still active. Because they shared that fixture, their results
are retained but are **not promoted to independent qualification**. In particular,
the cross-process control used an invalid synthetic token to exercise the real
CLI's credential-free network refusal and shared flock; it was not a successful
provider request by an external CLI process.

`003-r2-review.stdout`, `003-r2-review.stderr`, `receipt.json`, and the exact
`run_review.py`/`review-tests.swift` retain the result. The command was:

```text
/Users/andreyyurlov/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin/swift test --package-path /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/store-status-review-r2/input/cli --scratch-path /Users/andreyyurlov/.t3/worktrees/mixer/t3-84a22cd4/verification/plan-continuation-2026-11-07/store-status-review-r2/scratch -j 2 --filter 'StoreSubmissionReconciliationTests|StoreR2IndependentReviewTests'
```

Apple Swift 6.3.3, Xcode 26.6/17F113, SDK 26.5; managed test command 33.284 seconds,
exit 1. Limits: one attempt, 600 seconds, two jobs, 4 MiB per stream, 32 MiB total.
Actual managed output: 14,024 bytes. Source copy: 2,479,661 bytes before the small
review appendix, below 5 MB. Free space before build: 46,851,096,576 bytes.
All four canonical `Commands` entries have direct child reaped, both streams EOF,
owned group absent, and no cleanup errors. Only newly owned PGIDs 3604, 3607, 3608,
and 3609 were managed. No unknown custody or EPERM occurred. Completed scratch
328,413,387 bytes and temporary data 381,690 bytes were removed; `cleanup.json`
records the exact paths. No further process probe was made after terminal custody.

**Security and persistence assessment.**

R2 fixes the original source-level defect: `reserve()` sanitizes under the
identity flock before rewriting; recognized prior observations are removed,
never quarantined. Error paths call locked `observation()`, which also sanitizes.
`commit()` rereads current metadata under that same lock, so cooperating writers
share recognition. Fingerprints are byte length plus standard CryptoKit SHA-256,
not raw bearer text. Both admitted fields are searched by byte substrings.
Direct current-token matching additionally protects legacy records. A token over
256 bytes cannot fit in a production-admitted version (256 bytes) or state
(128 bytes); this explains omitting its fingerprint, not the count limit.

The retained `discardedThrough` generation is checked with the current observation
generation, preventing an older safe response from replacing a newer removed
observation. The isolated in-flight/rotated-writer, tombstone and safe-prior tests
passed in this attempt after fixture overlap ended. This supports R2's original
correction; the exact first regression is supported by producer evidence and
source inspection, not a clean repeat in this review.

Schema 1 decodes absent optional metadata. Read validation bounds and checks
fingerprint count, length, lowercase digest encoding and generation ranges.
Write validation now applies the same 16 KiB, depth-8 and 100-value limits before
persistence. Normal writes retain descriptor-relative opening, single-link
regular-file checks, two-second flock acquisition, file fsync, rename and
directory fsync. A failed persistence operation fails the command instead of
returning the unsafe observation. Removing a secret durably still depends on a
successful filesystem write; no disk-full/fsync/rename injection was attempted.

The reader and CLI are byte-identical to R1, and the original eight test bodies
and helpers are byte-identical. Consequently GET origin/identity checks, bounded
responses, current-response token checks, ignored error bodies/headers and
transport-diagnostic redaction were not weakened. Those eight groups passed
here. The prior 30-second deadline control was not rerun. Cross-process coverage
beyond retained R1 evidence and the provisional new control is not claimed.
Mixed old/new writers, hostile lock-file replacement, crash/power-loss durability,
unknown future credentials and already emitted copies remain outside this proof.

**Small corrective design and the boundary to preserve.**

The original P2 required durable removal of a *now-recognized* prior secret and
protection against stale/concurrent restoration. That is distinct from remembering
every credential ever supplied so that an unrelated future provider response
cannot reintroduce any of them. R2 implements the stronger historical rule and
adds a later-C regression for it. Do not silently drop that test, evict fingerprints,
reset the exhausted flag, or claim to recognize a credential before it is supplied.
Locked sanitization plus a monotonic recognition fence can satisfy the narrower
original boundary, but does not by itself satisfy that stronger all-future rule;
selecting that narrower contract must be explicit.

To preserve R2's stronger guarantee, the smallest compatible direction is to move
exact `(byteLength, SHA-256)` entries out of the bounded observation JSON into a
separate durable index under the existing per-identity lock. Append/deduplicate and
fsync recognition before reservation/commit/output; consult the index for both
prior and new values. A bounded-chunk journal can be a first implementation;
page/index it as needed to bound lookup work. Keep the observation record bounded
and keep the generation tombstone. Refuse a particular operation on unavailable,
corrupt or unwritable index storage, with an accurate recoverable storage error;
do not permanently close admission after an arbitrary number of credentials.
This retains exact history while allowing ordinary rotation and bounds working
memory instead of total lifetime queries. It needs executable concurrent-writer,
failure and >16-rotation tests before acceptance; it is a proposal, not a patch.

Migrate unsaturated schema-1 fingerprints under the lock. Already-exhausted R2
records did not retain subsequent fingerprints, so their full history cannot be
reconstructed merely by clearing the flag. Preserve that migration limitation
and define recovery explicitly; do not propagate the lossy saturation design to
new records. Increasing 16 or rejecting legitimate short JWTs is not a fix.

No product, candidate, tracking or pair9 file was changed; no child agent,
commit, push, provider-account call, token request, native/emulator/ADB/UI/capture,
physical-phone, held-process or held-scratch action occurred. After correction
and a clean independent review, root still owns integration of only the four
paths, the **103-input CI rebind and fresh six canonical consumers**, preserving
its current pair9 guards and other store slices. This report does not qualify
full W13, Play, D6, FieldLog, live ASC, or GA. Hashes and the closed artifact roster
are in `review-receipt.json`, `artifact-manifest.json` and `hash-seal.json`.
