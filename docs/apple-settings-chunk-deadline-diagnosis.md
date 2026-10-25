# Selected Settings PNG chunk deadline diagnosis

The selected iOS 26.5 run failed while uploading the **after-switch** PNG.
Request ordinal 166, Settings sequence 165, `settings-0118-png`, zero-based chunk
42 of 71 received only **0.008061916683800519 seconds** from the original
deadline calculation. Its first local failure was semaphore expiration. This
identifies the failed request and its admitted allowance; it does not identify
a slow server phase or establish that a transport change will pass.

The recommended next implementation is a coordinated, explicitly distinguished
**4,992-byte Settings upload format** using unescaped JSON slashes. Retain every
capture, file byte/hash, ordering predicate, durability operation, origin check,
existing request/body/storage cap, and deadline. This document selects no
implementation or native retry. Root must select the design first.

## Bound evidence and result

The frozen native handoff is
`3e068b73e1a5ee88227657f0708477e6e1feb3a99d20cfb95c0c9ca0e2339a53`.
The [offline audit](../verification/apple-settings-chunk-deadline-diagnosis/audit.py)
verified its 48 compact members and all 2,257 raw files, totaling 97,588,145
bytes, against the root manifest. The exact selected run is
`4c0ed51e-8060-4646-83a5-873b875d4d30`; its source revision label is
`4a4d8b7301351247318424ed71a89ab41f0db2ca` and source tree digest is
`2b44b02dbd702becefa8b609435928890ad7c1a5f7cb11b3cc0fd1f5000ca101`.

Source inspection uses the bound 32-file selected runtime archive
`765bd6b2caf703a65bf2f7d91e716f65c7b6cee6091a530e5106a96835dab13c`
and fresh 40-file accepted compile archive
`82b88c3ee0d55b3cf10930904f0f2eaed6d44b368659c9b2665f58cd28e764a9`.
Twelve exact inspected members are retained under this packet's `sources/`.
No live implementation is substituted. The prior bound baseline reconciliation
reports that all 13 actual V5 application files match fresh V6 and all 34 original
application/library sources remain unchanged. This lane verifies the selected
archives and raw files; it does not rerun that broader original/V5 comparison.
The stale template's focus preference is not an app change in this actual run.

Official results remain **Settings failed, dependent Tab skipped**; Xcode exited
65. The strict importer separately rejected
`Foreign/duplicate/incomplete selected test identity`. In the exact importer,
that combined predicate accepts only `Passed` or `Failed` selected methods;
the actual Tab node is `Skipped`. The message does not establish a foreign
identity or duplicate, and cannot replace the native Settings failure. It is
not a pass or a reason to relax the importer.

The bound native receipt records all five cleanup operations passing, the owned
simulator `0D9DB35F-E5A8-4ED6-A837-2CCD93DA939C` absent, both command groups
absent, scratch removed, and four baseline devices preserved. These are retained
root observations, not a new device/process inventory. Phones remain
disconnected and deferred.

## What this request establishes

The raw client stdout line 276 contains the one first-failure JSON record.
Its generation, sequence, slot, chunk index/count and request ordinal agree with
the helper receipt and the root result. Journal sequence 165 has exactly the
same generation, slot/index/count and declared payload hash as after-switch
observation 118. This is an explicit identity match; task identifier 166 alone
would not establish it.

The original transport returns `min(2.0, deadline - beginUptime)` after checking
the sticky first failure, the 2,500-request cap and the absolute deadline.
The retained values are:

| Client value | Seconds |
|---|---:|
| Start uptime | 943813.174526 |
| Initial and actual absolute deadline | 943842.174526 |
| Failing request begin | 943842.1664640834 |
| Actual allowance | 0.008061916683800519 |
| Failure diagnostic end | 943842.1796356251 |
| Begin-to-diagnostic interval | 0.013171541737392545 |

The diagnostic end is about 5.11 ms past the absolute deadline. This is the
whole issuing-path interval through cancellation/latching/diagnostic entry,
not a server duration. The client still computes its allowance before JSON
serialization/task creation and waits for that relative allowance later.
The fixed error text `request timeout within existing2second budget` comes
from this branch; two seconds was its ceiling, not its actual allowance.

All 166 raw journals, sequences 0 through 165, have committed outcomes with
resolved retirement and empty ancillary arrays. The transaction guard is absent.
Sequence 165 therefore committed durably even though the client timed out.
Commit does not prove timely reply delivery or callback scheduling. The
supplemental record has null HTTP status and error code, so neither is guessed.

## Observed costs and missing proof

These intervals use only client uptimes; host receipt times are not subtracted
from client times. An observation timestamp precedes its `post()` admission and
therefore supplies only an upper bound on remaining allowance.

| Record | Client seconds since start | Initial deadline remaining upper bound |
|---|---:|---:|
| Settings launched, sequence 1 | 3.606694 | 25.393306 s |
| Last route-opened observation, sequence 41 | 15.929228 | 13.070772 s |
| Before-switch observation, sequence 46 | 18.644295 | 10.355705 s |
| Switch-action marker, sequence 117 | 24.004857 | 4.995143 s |
| After-switch observation, sequence 118 | 25.480998 | 3.519002 s |
| Failing chunk's record, sequence 165 | 28.991937 | 0.008063 s |

The before-switch capture itself lasted about 1.360265 seconds; the after-switch
capture lasted 1.442506 seconds. The 5.360562 seconds between before observation
and action marker includes 70 serial chunk posts, fresh public switch queries,
action validation and the tap. It is not an upload-only measurement. The
3.510939 seconds between after observation and the failing chunk's record
includes serial uploading and all corresponding client/server work. No
per-request acknowledgement times or server phase spans were retained.

The before observation declares 10,653 AX bytes and 199,936 PNG bytes: 4 AX
chunks plus 66 PNG chunks. After declares 10,685 AX bytes and 216,421 PNG bytes:
4 AX chunks plus 71 PNG chunks. All after AX chunks and PNG indices 0 through
42 committed. The remaining 28 PNG chunks, terminal observation/files,
termination markers, completion marker and official passing Settings evidence
are missing from the accepted prefix. There is no terminal declaration from
which to infer its PNG size or future request count.

The audit replayed exactly these 166 records through the byte-exact original
selected `Session` validator using in-memory persistence callbacks. Every
complete reassembled file matched the raw published file. The original strict
summary still has `settingsEvidenceComplete = false` and
`setupObservationSatisfied = false`, pending `settings-0118-png`, and no
terminal/completion. This is a validated incomplete prefix, not native success.
Although after-switch sequence 118 supplies an enabled sample within the
unchanged three-second window, that sample alone cannot satisfy full setup.

The selected sources show origin/module validation, draft copying, validation,
durable journal/payload publication and guard retirement, then summary
persistence before the response write. These are possible costs. Their native
durations and the causal failing phase remain unmeasured. No diagnosis here
attributes the timeout to fsync, hashing, HTTP, PNG capture or scheduling alone.

## Narrow fixed-format design

Current `ToggleUITests.swift:106-110` computes
`count = ceil(bytes / 3072)` and slices at 3,072-byte boundaries. The selected
`settings_telemetry.py:17,230-255,326-331` uses the same constant, expects each
index to equal the number of accepted parts, requires the declared count/hash
and byte length to match the observation, admits at most 4,096 base64 characters,
and checks exact canonical decoding/reassembly/hash before publication.

Use a fixed 4,992-byte chunk in both endpoints. The new count is
`(bytes + 4991) / 4992`, maximum PNG count 401 with indices 0 through 400, and
maximum AX count 41. Its maximum base64 string is **6,656 bytes**. Keep the
per-request decoded length exactly
`min(4992, declaredBytes - index * 4992)`, strict canonical base64, exact total
length/hash, PNG validation, UTF-8 AX validation, and ordered slot retirement.
Do not accept arbitrary client-selected chunk sizes.

JSON serialization must explicitly use `.sortedKeys` together with
`.withoutEscapingSlashes`, retaining the existing `body.count <= 8192` guard.
All base64 characters then occupy one ASCII byte each in their JSON string.
The 41-row finite Foundation probe shows why this is required: a 3,072-byte
all-`0xff` payload can produce an 8,529-byte body with current slash escaping;
4,096 bytes can produce 11,262 bytes with escaping. The corresponding unescaped
4,096-byte maximum-metadata rows reach 5,803 bytes. The proposed 4,992-byte
format also has finite full/partial slash-heavy rows, reaching 6,995 bytes in
the maximum-metadata final-chunk probe. Exact rows are retained in the probe JSON. This probe tests encoding,
not a valid complete PNG/Settings run.

There is **no new metadata admission restriction**. From the exact closed
chunk fields, the fixed encoded envelope excluding `uptime` and `data` is at
most 316 bytes: fixed case/kind/keys; a 36-byte UUID; 64-byte hex digest;
17-byte `settings-NNNN-png` slot; and existing bounded integer fields. Those
allowlisted strings contain no slash, quote, backslash or control character.
Only the base64 string needs the explicit slash option.

The source delegates binary64 formatting to Foundation. Finite extrema probes
observe tokens up to 23 bytes, but do not prove its maximum across every finite
Double. A conservative nonnegative binary64 exact fixed-decimal ceiling is
1,076 bytes: values below one have at most 1,074 fractional places plus `0.`;
values at least one with fractional bits need far fewer places, and finite
integers need at most 309 digits. The exact `2^-1074` decimal expansion is
retained as a 1,076-character arithmetic assertion. This is a conservative
representation bound, not a claim that Foundation actually emits that token.
Consequently `316 + 1076 + 6656 = 8048`, leaving 144 bytes within the unchanged
8,192-byte cap. The 4,096-byte alternative gives `316 + 1076 + 5464 = 6856`,
leaving 1,336 bytes. Neither endpoint has a power-of-two constraint: both use
integer division, multiplication and slicing. The 4,992-byte size is divisible
by three, so complete chunks have no base64 padding; a final partial chunk
retains canonical padding. A 1,024-byte metadata envelope is not proven by this lane's
selected sources and finite probe. At 5,120 decoded bytes the same conservative
calculation is `316 + 1076 + 6828 = 8220`; that larger candidate needs an
additional platform-formatting proof. No arbitrary metadata truncation or new
guard is proposed to make it fit.

Distinguish the new fixed wire format before accepting setup. A narrow option
is mandatory `chunkBytes: 4992` on start, exact validation and echo in the start
reply, and a client requirement for that echo. The old host rejects the extra
start field; the new host rejects an old start lacking it. A mismatched packet
must fail before a committed start/cursor advance. No implicit negotiation,
retry, automatic old-format fallback or mixed-chunk session is permitted.
The discriminator and echo occur only on start; they add zero per-chunk bytes
to the 316-byte envelope. New count/index maxima retain three decimal digits,
so that envelope remains valid. Root can select the exact frozen old or new
packet as a whole.

For the eleven file descriptors actually observed in this run, complete upload
arithmetic changes from 179 to 116 chunk requests. Before-switch changes from
70 to 44; after-switch from 75 to 47. The wider-margin 4,096-byte alternative
would require 134 overall, 52 before-switch and 56 after-switch. These are counterfactual counts for the
same declared file sizes, including after's incomplete PNG. They are not a
predicted elapsed saving, a completed upload or evidence that 29 seconds will
suffice. Later sequence-derived slot names will change; content hashes and
observation/action links must be generated consistently, never relabeled from
the old run.

## Required proof and future implementation controls

Preserve all seven observed route AX captures, every route search/tap/opened
witness and allowed retry, fresh public parent/leaf/action binding, before,
after and terminal PNG **and** AX, optional bounded polls, the anchored
three-second enabled observation rule, terminal enabled state, official passing
Settings JSON/screenshot attachments, termination and test-completion markers,
and unchanged strict official method/attachment/native oracle import. The
optimization changes only chunk packing and its explicit session format.
It cannot substitute summary metadata for a file, reuse a screenshot, skip
proof, or advance an observation while a slot remains pending.

Keep the 2,500-request cap; 8,192-byte request and client-response caps;
200,000-byte AX and 2,000,000-byte PNG caps; 7,000,000 aggregate declared bytes;
32 uploads; 100 events; 40 polls; client and host 29-second session checks;
two-second request ceiling and sticky first failure. Preserve the same
capability/framing/origin checks, sequential request execution, response bounds,
transaction guard, exact publication/commit/retirement and ancillary semantics.
The existing request/body/file/count bounds still bound persistent storage;
no new queue, concurrency, deferred durability or extra diagnostic write belongs
in this change.

Before another compile/native selection, a reviewed implementation needs finite
executable controls for:

- Exact Foundation bodies with maximum allowed metadata, slash-heavy/all-byte
  payloads, finite extrema, complete and final partial chunks. Verify actual
  UTF-8 size, guard rejection above 8,192, and unescaped decoded equivalence.
- Sizes 1, 4,991, 4,992, 4,993, exact multiples, maximum AX and maximum PNG;
  exact last length/count, canonical base64, reassembly bytes and SHA-256.
  This lane already checks split/reassembly arithmetic for ten complete native
  files and nine finite boundary payloads for both candidate sizes; it implements no new receiver.
- Explicit old-client/new-host and new-client/old-host rejection before commit;
  wrong/missing format echo; mixed 3,072/4,992 fragments; wrong count/index/slot,
  duplicate/reordered/missing/oversized chunks, malformed encoding, digest/length
  disagreement and corrupted PNG/AX. Rejection must not advance accepted state.
- Full strict public Settings proof on a valid derivative fixture, with each
  required capture/witness/action/deadline/termination/completion individually
  missing, stale or invalidated as negative controls. Keep the official importer
  and original application oracle byte-identical; only the closed upload-format
  validator/arithmetic should change.
- Existing commit-point/rollback/retirement/failure injection and request/body/
  aggregate/storage/deadline/sticky-failure controls. A larger chunk does not
  authorize acknowledgement before durable commit or origin-check caching.

A fresh source-bound package and independent review must precede any later
root-selected native attempt. Only an actual passing full Settings proof and
the separately imported selected diagnostic can support that development slice.

## Verification and limits

[Findings](../verification/apple-settings-chunk-deadline-diagnosis/findings.json),
[audit receipt](../verification/apple-settings-chunk-deadline-diagnosis/audit-command-receipt.json)
and [Foundation receipt](../verification/apple-settings-chunk-deadline-diagnosis/host-command-receipt.json)
retain commands, Python 3.14.8/Swift 6.3.3 versions, compiler/source hashes,
stdout/stderr, exit codes and scopes. The host executable used an explicit
macOS 26 SDK target; its executable/module-cache scratch was removed.
No selected producer, broad historical suite, native product, listener, device,
phone, UI, screenshot, Git operation, live service or excluded frozen lane was
queried or executed. Only this lane's documentation/evidence files were written.

The diagnosis grants no Settings/Tab pass, keyboard/carrier completion, full
matrix, immutable external FieldLog dogfood, signing, store, operational or GA
acceptance. Causal server phase, new-format behavior and any timing improvement
remain unverified. The original native and importer failures stay authoritative.
