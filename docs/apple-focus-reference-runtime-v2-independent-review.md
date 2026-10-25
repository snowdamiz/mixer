# Apple reference-first runtime v2 independent host review

**Rejected for native dispatch.** The frozen driver rejects files that its own
composed bridge and durable Settings store always create. The 111 producer
controls pass in an isolated copy. Of 33 additional independent controls,
23 pass and 10 fail, with no errors or skips. No simulator, device, compiler,
native tool, UI/capture operation or service was invoked by this review.

The reviewed handoff is
`78ada9ff4aa3392e07f4fdf71a0eb563c67c8fde920388609372b09a771f3668`;
the packet is
`8a6be8d06285c3fd25bdb9bc2c589ea87a7677d8a6b9b6e0545b23076cd6a7b6`.
The accepted checkpoint and root acceptance cover the reference source,
retained compilation and classifier consistency. They do not accept this driver
or authenticate a future run.

## Confirmed driver blocker

`adapter.application_captures` at producer lines 59–69 permits only eight fixed
application filenames and names beginning `0000-settings-`. The actual retained
`Bridge.__init__` immediately calls `persist_summary`, creating
`bridge-summary.json`. The actual durable `Session.request` start commits through
`TransactionStore`, which retains `.settings-attempts/`. Settings AX and PNG
payloads are published as `settings-NNNN-ax.txt` and `settings-NNNN-png.png`.
Every one of those normal names fails the capture inventory predicate.

The independent probe imports the entire frozen composition with the exact
compiled products materialized, forbids subprocess launch and socket
bind/connect, constructs its actual `h.Bridge`, and executes the actual Session
start and TransactionStore publications. It observes:

| Actual host operation | Normal retained output | Capture result |
| --- | --- | --- |
| Composed bridge construction | `bridge-summary.json` | Rejected |
| First Session start commit | `.settings-attempts/`, `0000-settings-0000.json`, summary | Rejected |
| TransactionStore AX/PNG publication | `settings-0001-ax.txt`, `settings-0001-png.png`, journals/attempts/summary | Rejected |

All three fail with `Unexpected generation/action capture rejected` while the
transaction guard is absent, retirement is complete and persistence is certain.
This uses synthetic host payloads, including a generated one-pixel PNG; it is
not a screen capture or native observation. The retained previous runtime
capture inventory independently contains the same summary, attempts directory
and AX/PNG filename families.

Evidence: [actual bridge output](../verification/apple-focus-reference-runtime-v2-independent-review/attempt-2/actual-bridge-inventory.json),
[historical inventory](../verification/apple-focus-reference-runtime-v2-independent-review/attempt-2/historical-capture-inventory.json),
and the exact probe source in
[run_review.py](../verification/apple-focus-reference-runtime-v2-independent-review/run_review.py).
The native wrapper would latch this reporting failure and cannot produce a
diagnostic import even if the two XCTest methods finish normally.

Repair in a new versioned packet should distinguish validated auxiliary bridge
and Settings evidence from the four authoritative application observations.
Keep unresolved transaction guards, ancillary failures, unexpected actions,
foreign generations, redirected paths and unrecognized data fail-closed. A broad
filename-prefix exemption would not establish that distinction.

## Additional synthetic consistency failures

These are separate from the actual driver inventory blocker. They demonstrate
acceptance of contradictory or mistyped capture metadata inside explicitly
synthetic capsules; they do **not** demonstrate a native-provenance exploit.

| Failure family | Controls | Observed result |
| --- | ---: | --- |
| Baseline `commandGeneration=2.0` | 1 | Accepted as the required integer command generation |
| Signature inode boolean, negative/floating byte length, malformed SHA256, including both signatures changed | 7 | Accepted malformed signature shape |
| Baseline/after file mtime moved after the official premise attachment | 1 | Accepted contradictory baseline ordering |

Each returns `one-strict-original-verdict-passed`, input count 1 and the internal
`provenanceAccepted` field true in a **host synthetic capsule**. The importer
strictly checks the signature's mtime integer and broad run interval, but does
not validate its other fields. Its command-generation comparison uses Python
numeric equality. It also lacks a baseline-versus-premise wall-time order check.
An ordering repair must account explicitly for the precision of official
timestamps; it must preserve unchanged app files when no app focus update occurs.
Do not invent a digest by reserializing a decoded app observation: the retained
signature describes the original file bytes.

The nine fixtures and complete returned results are retained in
[control-results.json](../verification/apple-focus-reference-runtime-v2-independent-review/attempt-2/control-results.json).
The complete failed assertions are preserved in the independent stderr log.

## Execution and provenance audit

The inspected dispatch path checks the exact reviewed packet and the root's
out-of-band selection SHA256 before importing runtime composition. A fresh root
selection binds the run UUID, one owned device, complete pre-creation baselines,
pinned developer directory and exact source/product identities; dispatch rejects
stale/future selection and an existing run output. The complete product archive
remains `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`;
the reference source tree remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`.

The command selection requires the exact two methods, one selected destination,
canonical 0700 session and absent result. The selected `Commands.run` path uses
the unchanged observer V2, records result identity, exports official attachments
once, and calls the canonical runner for official summary and tests traversal
against that result. It checks exactly two unique complete test executions,
Settings pass, one device/configuration, outcome counts and run interval before
attachment joins. Capture then binds the actual returned traversal strings,
first export inventory, attachment bytes and application files in an immutable
in-process capsule. The canonical runner already strips textual stdout/stderr;
its captured strings are not a byte-for-byte copy of original tool pipe output.

Plain JSON caller data and a constructor call without the private token are
rejected. Python's private token is a trusted-code convention, not isolation
against arbitrary code running in that same interpreter. Matching JSON IDs,
self-produced receipts and host-created capsules cannot authenticate a native
run. The necessary native boundary remains the separately selected root driver
actually running its pinned command and capturing official output once.

The 111 producer controls and independent controls retain rejection evidence for
foreign/replayed/duplicate/missing executions and attachments, source/product
substitution, contradictory witness data, invalid JSON, result/session swaps,
app symlinks, result substitution during traversal, failed commands, unobserved
EOF, incomplete cleanup and stale/future selection. Passing premise with missing
return evidence remains unknown; it is not zero injection. Strict pass/fail and
bound false-premise outcomes remain diagnostic only. All broad `runPassed`, full
case/cursor/keyboard, carrier and GA flags stay false.

## Retained attempts and limitations

The executable command for attempt 2 is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v2-independent-review/run_review.py --attempt 2
```

Python is 3.14.8 on Darwin 27.0.0 arm64. The inherited compilation revision label
is `ba9ad4372f94463ba4d363cdfd76dd565c96413f`; exact frozen source/input/output
SHA256 values define this review, with no Git query. The final receipt is
`3f4303a03dbcc955d6b7156b3ecf4db7d1a4466bcf14cf1c956f8e287a9cd6af`.
All 124 bound inputs are unchanged before/after. Full source/product test scratch
and probe state are removed; reviewed source copies, logs and counterexamples
remain under the review's owned directory. Other projects were not touched.

Attempt 1 preserves the same 111 producer passes and 10 independent failures.
Its receipt finalization called `platform.platform()`, which attempted a
`uname -p` subprocess. The independent host guard rejected it before process
launch. The reviewer-only metadata path was changed to `os.uname()` and attempt 2
was retained separately; no first output or producer evidence was overwritten.
The first file-only seal attempt also rejected the bound official SDK version
alias before writing a handoff. Its source and failure remain preserved; the seal
now permits only that exact official alias and rehashes its canonical target.

This is a host consistency/composition review. It does not execute or approve
the native run, attest real keyboard delivery, rerun compilation, prove platform
parity, qualify immutable published FieldLog consumption or satisfy signing,
store, operational, physical-phone or GA gates. Phones remain disconnected and
deferred. Root may select one fresh owned simulator only after a repaired packet
receives separate review. The hosted authority/catalog lane was not accessed.
