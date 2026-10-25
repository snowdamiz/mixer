# Offline Settings bridge timeout diagnosis

The retained failure establishes deadline pressure during the terminal Settings
upload. It does **not** establish a request taking more than two seconds, a
specific slow server operation, or the identity of the timed-out bridge request.
The smallest defensible next change is a first-failure client diagnostic that
records the actual remaining budget and exact request identity. No product,
importer, native packet, budget, or frozen source was changed by this diagnosis.

## Exact evidence and scope

The input is the single failed run `e7108fc8-281b-4c59-831a-f3697609017d`, bound by
[native handoff](../verification/apple-focus-reference-v5-native/handoff.json)
SHA-256 `bc226729d7133f33b52d98a4fd7446771bae7bc6c5672455927bbe343c723927`.
The inherited compile label is `ba9ad4372f94463ba4d363cdfd76dd565c96413f`;
the exact compile-source tree is
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`,
selected runtime-source tree is
`8f6c2d184964d88df9fc29352f52bc78644b68f23d7538925e567f6247c1bf0c`,
and unchanged native product archive is
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.

The native output root is
`verification/apple-focus-reference-runtime-v5-namespace-correction/native-run-v5-e7108fc8-281b-4c59-831a-f3697609017d`,
with inherited full output-tree hash
`2ca1fa6eae1eea42dffa857996574e992bb20d1deeba417377fbf39ebed63751`.
Root's earlier verification covered 41 producer members, eight external inputs,
and 2,455 native output files. This lane independently checked the handoff and
the exact source archives and read only the files listed in
[evidence bindings](../verification/apple-settings-bridge-timeout-diagnosis/evidence-bindings.json).
It did not repeat the full output-tree collection.

[Source bindings](../verification/apple-settings-bridge-timeout-diagnosis/source-bindings.json)
identify each exact archive member inspected. The two Swift files come from
`accepted/harness/UITests/` in the bound `accepted-sources.tar.gz` nested inside
the V5 frozen input archive. The Python sources come from the correction's
bound `runtime-sources.tar.gz`, under `selected/`. References below are line
numbers in those exact members. No live checkout implementation was substituted.

The [findings](../verification/apple-settings-bridge-timeout-diagnosis/findings.json)
retain normalized timeline calculations and raw log line identities. All 221
Settings journal records and their 221 attempt outcomes were read: sequences
0 through 220 are contiguous, every outcome is committed, every recorded guard
retirement is resolved, ancillary arrays are empty, and the transaction guard is
absent. This proves durable outcomes for those records; it does not prove that
the client received their replies.

No iOS simulator execution, UI or screenshot query, device query, retry, listener,
Git operation, shared-tracker edit, or excluded hosted-lane import occurred.
Original failures are retained. Owned extraction, binary, module-cache, and
synthetic transaction scratch was removed; the cleanup receipt records this.

## Client deadline and failure path

`DiagnosticTransport.swift:28-37` admits each request only while the client
deadline remains and returns `min(2.0, deadline - now)`. This is a two-second
ceiling, not a guaranteed two-second allowance.

`ToggleUITests.swift:34-45` sets the client deadline to the start uptime plus
29 seconds, then can only shorten it using the start reply. Launching Settings,
route discovery and actions, snapshots, PNG/AX construction, serialization,
uploads, and replies consume that same interval. `settings_telemetry.py:21` also
sets `MAX_DURATION = 29.0`; host and client limits are separate checks.

For every Settings post, `ToggleUITests.swift:16-32` obtains the allowance
before JSON serialization and task creation, sets `URLRequest.timeoutInterval`
to that allowance, and waits on a semaphore for the same allowance. The
semaphore wait starts later than the budget calculation; its relative timeout
is not a separately measured absolute deadline. If the wait expires, it cancels
the task and latches the fixed text
`request timeout within existing2second budget` regardless of the actual
allowance. The raw first setup error at stdout line 303 contains that exact
text, which identifies the semaphore-expiration branch in the retained client
source. It does not expose the branch's remaining value or request identity.

The retained runner log also reports `NSURLErrorDomain -1001` at line 300 for
URLSession task `<2D5B6493-B66A-474E-8A31-D4E051B2AC11>.<221>` to `/evaluate`.
That is a Foundation task identity, not an explicit bridge sequence binding.
It must not be relabeled as Settings sequence 220 or 221.

The first network failure is deliberately sticky. `DiagnosticTransport.swift:29`
rejects later attempts before issuing a request, and `:35-37` preserves the first
failure. The subsequent terminal capture attempt still performs local public
queries and capture work before reaching telemetry, then its post fails with
`prior bridge failure`. Termination and completion marks fail the same way.
Those later errors explain missing completion evidence; they do not identify
the original request or supersede its failure.

## Timing established by retained records

The client start record gives uptime `939365.989950875`, so its initial deadline
is `939394.989950875`. The calculations below use only client record uptimes;
they do not subtract host and client clock values.

| Retained record | Seconds since client start | Maximum time left before `post()` |
|---|---:|---:|
| Before-switch observe, sequence 47 | 19.995474167 | 9.004525833 s |
| Switch-action mark, sequence 118 | 24.302617167 | 4.697382833 s |
| After-switch observe, sequence 119 | 25.286335042 | 3.713664958 s |
| After-switch PNG final chunk, sequence 194 | 27.372891292 | 1.627108708 s |
| Terminal observe, sequence 195 | 28.353645792 | 0.646354208 s |
| Last committed PNG chunk, sequence 220 | 28.987842542 | 0.012157458 s |

These are **upper bounds**: `send()` stamps `record.uptime` before `post()` calls
`begin()`, and the client deadline cannot increase. The actual allowances were
not retained. In particular, the last durable request could have received no
more than about 12.16 ms, despite the fixed two-second failure wording. The
timed-out request remains unknown.

The terminal observation declares a 10,685-byte AX file and a 217,989-byte PNG.
With fixed 3,072-byte chunks, it requires 4 AX requests and 71 PNG requests after
its observation request. Its retained records contain all 4 AX chunks and PNG
indices 0 through 20. Fifty terminal PNG chunks remain outside the committed
prefix. The before- and after-switch uploads had already consumed 70 and 75
chunk requests respectively. These counts demonstrate substantial serial
upload work inside the existing overall deadline, without proving any single
server operation was slow.

`receivedUptime` is sampled inside `Session._request()` after outer binding
checks and the draft-state copy. It is not HTTP arrival time, commit time,
response-write time, or client acknowledgement time. Inter-record gaps also
include client work. They cannot measure server latency or attribute the
timeout to filesystem syncs.

## Server work before the reply

The retained sources establish this successful-path ordering:

1. `harness.py:344-346` starts one `HTTPServer` loop on one background thread.
   `bridge.py:196-218` validates loopback, capability, framing, body bounds and
   JSON, then calls `bridge.request()`. The socket's separate `settimeout(2)`
   bounds blocking socket operations, not all Python validation and disk work.
2. `composition.py:75-87` checks selected source/module bindings before
   dispatching Settings. `runtime_bindings.py:18-22,59-70` hashes selected
   source/data files and validates the loaded module closure. These checks
   execute on each request.
3. `settings_telemetry.py:194-212` copies draft state, validates and assembles an
   intent, then commits it before advancing accepted state and returning the
   result. Chunk upload is serial and ordered. Final chunks additionally
   assemble, hash, validate, and persist the complete file (`:233-255`).
4. `durable_settings.py:144-226` durably writes the transaction guard and staged
   journal, syncs their directories, hard-links and verifies exact publications,
   and syncs the publication directory. This is the irrevocable commit point.
   Guard retirement and the committed attempt outcome happen afterward, still
   before `commit()` returns. A normal journal-only success uses eight fsync
   calls in total. A final chunk also durably writes its completed payload.
5. `settings_telemetry.py:406-422` persists the bridge summary before returning.
   `bridge.py:66-79` performs one file and one directory fsync for that summary.
   The normal journal-only path therefore performs ten fsync calls before the
   response is attempted. This count is source/control evidence, not measured
   native latency or a causal finding.
6. Only then does `bridge.py:218-232` encode the result, send headers and write
   the response. Durable commit and a successful client acknowledgement are
   distinct events. The retained empty bridge failure list does not prove
   delivery within the client's allowance.

Server-side origin validation, draft work, durable commit, postcommit reporting,
reply delivery, and callback scheduling are possible contributors. The retained
run has no per-phase duration or shared client/server request identifier that
can discriminate them. It provides no basis to select one as the cause.

## Smallest next instrumentation

Add one bounded, sanitized first-failure diagnostic in the Settings client's
`post()` path. Preserve the current allowance, request cap, body cap, sticky
failure, and all setup predicates. Retain these values locally while a request
is in flight and emit them only on its first failure:

- Bridge kind, generation, sequence (or explicit start), stage, slot and chunk
  index/count where present; request ordinal and URLSession task identifier.
- Client monotonic begin and failure uptimes, absolute deadline, actual allowance,
  and whether the overall deadline clipped the two-second ceiling.
- Failure branch: begin-deadline, semaphore expiration, Foundation error, HTTP
  rejection, or invalid response; safe status/error code when available.

Do not log capability headers or PNG/AX body bytes. The semaphore-expiration
path must not read the asynchronously mutated callback box without proper
synchronization. Its request identity and calculated allowance are already
available in the issuing path, so the minimum diagnostic needs no such read.

If the next question is server latency attribution, add bounded in-memory
phase spans keyed to the same bridge identity: HTTP dispatch, binding check,
validation, commit point, retirement/outcome, summary, and response write.
Persist those spans once during cleanup with failure clearly reported as
ancillary. Repeated per-request durable diagnostic writes would themselves
alter the path being measured. This server tracing is additional instrumentation,
not a demonstrated transport fix.

A refreshed packet and independent review would be required for a later native
selection. This offline result authorizes no retry. The current evidence is
insufficient to justify a deadline change, relaxing durability/origin checks,
or an importer correction.

## Host controls and completion boundary

The [host controls](../verification/apple-settings-bridge-timeout-diagnosis/host-controls.json)
ran exact retained original code only:

- Five Swift assertions check an ample allowance, the approximately 12.16 ms
  example at the last durable record's timestamp, deadline rejection without
  issuing a request, first-failure preservation, and rejection after failure.
  That timestamp is a synthetic input to the control, not a recovered timeout
  identity or actual allowance.
- One synthetic journal-only transaction through original `TransactionStore`
  and `DiskIO` records eight fsync operations, committed outcome and guard
  retirement. It does not replay the native run or measure its disk performance.

Commands, Swift 6.3.3/Python 3.14.8 versions, exact source hashes, compiler hash,
outputs and exit codes are recorded. The first host compiler invocation could
not load a standard library for its default macOS 28 target. That failed
[host attempt](../verification/apple-settings-bridge-timeout-diagnosis/host-control-attempt-1.json)
is preserved; the control passed with the pinned MacOSX SDK and explicit macOS
26 target. No native product target was changed.

Settings remains failed, dependent `test010ReferenceFirstTab` remains skipped,
and no diagnostic or qualification pass is credited. The importer correctly
rejects the incomplete run. The earlier native cleanup and baseline preservation
remain the root-bound evidence, not a new device inventory from this lane.
Physical phones remain disconnected and deferred. This result grants no
keyboard/carrier completion, full matrix, immutable FieldLog dogfood, signing,
store, operational, or GA acceptance.
