**R3 candidate delivered; NOT QUALIFIED and not ready for integration.**

The two permitted host attempts are exhausted. Attempt 1 compiled and ran 19
serialized test groups: 18 passed, while the new 24-writer control threw a
`store.local-record` error. Its cause remains unresolved. Attempt 2 compiled the
final production implementation but failed compiling the newly added maximum-field
probe because its closure needed an explicit throwing type. That one annotation
has been corrected after the attempt, without another compile or execution.
There is no passing final-suite result. Do not treat the rotation successes below
as acceptance of the full candidate.

All work is confined to this `store-status-fix-r3/` directory. The four product
paths are mirrored under `candidate/`; canonical parent files are unchanged.
The parent must keep its owning 101-input closure unchanged until a corrected
candidate passes review and qualification. No tracking files or other lanes were
edited, and no commit, push, child agent, native/device/emulator/ADB/UI/capture,
cloud, provider/account call, credential request or publication occurred.

**Frozen inputs and preserved history.**

The product base is `96f03ab65966a6374e958e780fa09a3eed814c0b`, tree
`6dacea5d2f5cd55d6934142cce556a4bd0fcd1c0`, independently of subsequent parent
metadata changes. The four R2 files were imported from
`/Users/andreyyurlov/.t3/worktrees/mixer/t3-efc61fb9`; each matched the frozen
`patch-manifest.json` and the producer's input snapshot. The full frozen patch
SHA-256 is `e0937f48f97f3c70264364285f77b07917daa9f478fdcba22193aec1d32b68d0`.
`import-receipt.json`, `frozen-r2-patch-manifest.json`, the full frozen R2 patch,
and `frozen-r2/` retain this proof.

Both parent review reports were read in full. R1 reproduced B remaining on disk
when B became the current credential; the 401 report hid it, but a later missing
credential invocation emitted it. R2 introduced locked recognition/sanitization,
in-flight protection and a generation tombstone, but its 17th distinct short
credential permanently froze admission. The R2 review's new JWT success-rotation
probe was **inconclusive**, because two serialized suites still ran concurrently
against their shared static fixture. The isolated frozen R2 saturation control
**did** reproduce the permanent lockout. No result here rewrites that history.
The original bad saturation test is retained verbatim in
`frozen-r2-saturation-test.swift`, as well as the complete frozen R2 source.

**Proposed design and comparison.**

A bounded-chunk append journal uses bounded memory, but a full membership scan
still grows with lifetime history; stopping that scan at a quota would eventually
block progress again. It would need a separate index to bound lookup work.
The candidate therefore uses direct `(byteLength, SHA-256)` hash files, one fixed
length-presence header, and a single pending-recognition journal under the
existing identity flock. No new package dependency is introduced; hashing uses
the existing `SourceDigest` implementation backed by CryptoKit.

A new fingerprint first enters an atomically published, fsynced `pending` file.
The operation then publishes its length bit, its exact fingerprint file, and
fsyncs the directory before removing and syncing the pending entry. Opening the
index replays a valid pending entry before reservation, commit, prior-observation
reuse or output. Existing fingerprints are validated and synchronized, rather
than duplicated. No plaintext token is written to these files or their names.
Normal temporary-file paths are descriptor-relative, exclusive, no-follow and
removed on scope exit. Opened header, journal and fingerprint files must be
single-link regular files. The observation still uses the existing atomic
rename/fsync discipline and the `discardedThrough` generation tombstone.

The observation is schema 2 and remains bounded to 16 KiB, depth 8 and 100 JSON
values; credential count is absent from it. The schema-1 limit of 16 applies only
to validating the old migration input, never to new recognition. The index header
is 348 bytes and contains 256 length flags plus a SHA-256 checksum. Header reads
are capped at 513 bytes; individual entry and pending reads at 129 bytes. A lookup
checks only substrings of the admitted 256-byte version and 128-byte state:
at most 32,896 + 8,256 = 41,152 membership probes per observation when all lengths
have occurred. A status operation can consult at most four observations through
reserve, commit and error fallback, so this bound is independent of lifetime
credential count. It is a work bound, not a measured latency guarantee. Filesystem
storage grows with distinct credentials; physical capacity errors remain possible.

The maximum-length probe was added specifically to exercise all 256 length flags
and maximum admitted fields, but it did not execute because of the attempt-2
compile failure. This worst-case workload remains unqualified.

**Important integrity limit of this direct-file proposal:** malformed present
headers, pending entries and looked-up fingerprint files fail closed; missing
schema-2 index directories also fail closed. However, a deleted individual hash
file is indistinguishable from a fingerprint that was never present. This is not
an authenticated anti-deletion or rollback index, nor a global audit of all hash
files. If the required corruption contract includes detecting lost individual
entries, this design needs a referenced, integrity-checked page/tree structure
before acceptance. Do not claim complete corruption coverage from the passing
malformed-file controls. This limitation and the unresolved concurrency failure
are material review issues, not accepted exceptions.

**Migration and recovery contract.**

Schema-1 records without fingerprint metadata migrate under the same lock.
Unexhausted R2 fingerprints are recognized and synchronized before removing their
old JSON metadata. Known prior observations are then removed and their generation
tombstone retained. Tokens longer than 256 bytes cannot occur within either
admitted field and do not need substring fingerprints; the current-token reader
checks remain unchanged.

Exhausted R2 records return `store.credential-history-incomplete` without modifying
the record or creating an index. R2 lost the seventeenth and later fingerprints;
clearing its flag cannot recover them. No reset, eviction, lifetime counter,
customer migration command or user-data migration is included. Safe future
recovery would require complete independently retained recognition evidence;
this candidate does not assert that such evidence exists.

Unavailable, malformed or unwritable index state returns
`store.credential-index` for the operation. Correcting permissions or restoring
the exact intact state permits retry. The controls restore exact test backups;
they do not establish that deleting corrupt history is safe. A crash before the
initial journal is durably published cannot be claimed as durable recognition.
After that boundary, the staged replay controls cover journal-only,
journal-plus-length, and journal-plus-length-plus-entry states. They are ordinary
filesystem replay fixtures, **not process-kill, disk-full, partial syscall,
fsync-fault or power-loss tests**. Plain `fsync` does not establish drive power-loss
ordering; F_FULLFSYNC qualification did not run. Mixed old/new writers, hostile
replacement of lock/index inodes and rollback remain outside the evidence.

**Observed verification, including failures.**

All tests are in `StoreSubmissionReconciliationTests`, one serialized suite.
The R1 eight test bodies and original shared helpers are byte-identical. The four
R2 groups for recognized-secret removal, in-flight/later-C rejection, generation
tombstones and safe-prior bytes are byte-identical. Only R2's bad lockout test is
replaced, and the R2 cross-process review control is included in this same suite.
`original-eight-preservation.json` also compares directly against the R1 source
with SHA-256 `1656b7d597e91ce569724ca34332c1f78bd4a1e207ce2d33e4a88d38393f713b`.
The public reader and CLI remain byte-identical to R1/R2.

Attempt 1, `attempt-1/receipt.json`, ran in 52.665 seconds and exited 1. Its
selected suite ran 19 groups in 1.777 seconds. Passing groups included:

- 80 distinct successful credentials, including 40 locally ES256-signed,
  signature-checked 250-byte individual JWT fixtures; 40 further distinct
  credentials rejected with 401; exactly 120 retained entries; older and later
  historical-token reflections rejected; reused and 293-byte team-shaped tokens
  still progressed. These are synthetic inputs, not Apple acceptance.
- Partial header and entry corruption, a missing whole index directory and a
  permission-denied new recognition all refused safely, with successful progress
  after exact restoration. Symlink/hardlink entries and a malformed pending
  journal were refused without altering the outside control.
- Three interrupted-publication layouts replayed recognition before credential-free
  output, removed the unsafe prior, retained the fence and rejected later reflection.
- R1 and unexhausted R2 migration, explicit exhausted-R2 refusal, all original eight
  groups and four retained R2 security groups, plus the real-CLI-process recognition
  fence. The CLI process used a deliberately invalid synthetic token and performed
  no successful external provider call.

The new 24 simultaneous in-process writer group failed with a generic local-record
error after 0.067 seconds. The test threw while examining its results and did not
establish its final no-duplicate/generation assertions. No precise syscall cause
was captured, and none is claimed. Attempt-1 four-file source is retained and
hash-matched under `attempt-1-source/`.

For attempt 2, unnecessary newly added parent-directory fsync calls outside the
identity lock were removed to preserve the original constructor behavior. Safe
step/errno diagnostics were added for local-record failures. This is not claimed
as an experimentally established concurrency fix. The concurrency control was
expanded to five rounds; a maximum-field/all-length control was added. Attempt 2
ran 13.615 seconds, compiled and linked the final production module and CLI, then
failed compiling that new test's inferred nonthrowing closure. It ran **no tests**.
The attempted four-file source remains under `attempt-2-source/`. The only later
source change was explicitly typing that closure as throwing; it is uncompiled
and unexecuted. The final production bytes match attempt 2, while final test bytes
do not. `final-source-bindings.json` distinguishes every binding.

Both attempts used the canonical parent `Commands` runner, SHA-256
`c758c9685ef536968db06dfaf9f25450eac47db83fd2531a8caa2000cf793e1a`, Apple Swift 6.3.3,
Xcode 26.6 build 17F113, macOS SDK 26.5, and `-j 2`. The exact argv, environment,
source roster/digest, tool versions, command times and output hashes are in each
receipt. Limits were two attempts, 600 seconds each, 25 minutes total, 4 MiB per
stream, 32 MiB aggregate, source below 10 MB and owned scratch below 1 GiB. Final
source copy is 2,370,065 bytes across 116 files. Peak observed scratch plus temp
was 329,758,238 bytes; managed output totaled 19,698 bytes. The wrapper checks
scratch usage periodically and shortens the canonical command deadline on breach;
no breach was observed.

Every managed command has direct child reaped, both streams EOF, owned group
absent and no cleanup error. No unknown/EPERM custody occurred. `cleanup.json`
records removal of only this lane's `scratch/` (327,700,023 bytes) and `temporary/`
(410,015 bytes), after terminal custody. No further process probes or signals were
made. All named historical process/custody, FieldLog, v5 and frozen-lane holds
were untouched. No physical phones were accessed.

**Delivery and parent action.**

`implementation.patch` is the full four-path patch against frozen parent 96f03ab;
SHA-256 `ab210923850372d7bf5f20a50d27176ff43e94f25c788e99b4a41d1bd6dd3e11`.
`r2-incremental.patch` is the exact R2 increment;
SHA-256 `f3ee9e3bc5fd8b4f4e6460b7f3a8da9ff6447e7c0558204b8aee3cab594c980f`.
Both patches were mechanically applied in disposable owned directories and all
four resulting files matched the final candidate. `patch-checks.json` retains
those commands; these are patch-format checks, not runtime validation.

Final four-file hashes are:

| Path | SHA-256 |
| --- | --- |
| `cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift` | `21198f3f5a91f4666b66bb540ab9e14214381a142903b9c034e5cd30a260d8f5` |
| `cli/Sources/MixerBuild/StoreReconciliation.swift` | `e19445b4d84bc8961e10944cdc335ec0710ca29bc5ed8de5cb7bee5ea3f1dac5` |
| `cli/Sources/MixerCLI/main.swift` | `d6b235f63e551f09db526103b6bdae2e311f8d50890bf62d79bf37aec0e52a42` |
| `cli/Tests/MixerBuildTests/StoreReconciliationTests.swift` | `345603531cc3512b353c09e6e67c4e1b9cef82da822ac5a36a50441acb9539d6` |

Root should review the unresolved concurrency result and index-integrity contract,
then authorize a fresh bounded corrective/verification campaign. There is no
third-run shortcut in this wrapper. Only after independent acceptance may root
integrate the four files, retain its pair9 corrections, rebind the canonical
**103-input closure and run the actual six consumers**. None of those integration
steps ran here. Parent may commit metadata and accepted existing evidence only;
the canonical owning 101-input product state stays unchanged.

This does not qualify complete W13, live ASC, account-action taxonomy, upload,
Play, D6, separate-repository FieldLog immutable-package consumption, native or
physical acceptance, or any GA gate.
