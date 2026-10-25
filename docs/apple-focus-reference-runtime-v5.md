# Apple reference-first runtime preparation V5

V5 repairs the rejected V4 root-time precision, fixture closure, ambient Decimal
flags and incomplete-report namespace defects. This is host-only preparation.
The immutable packet must pass host controls, independent V5 review and a fresh
root selection before any separate native dispatch. Physical phones remain
disconnected and deferred. All runtime, keyboard, carrier and GA credit is false.

Root selected the schema 5 timestamp contract in coordination: canonical ISO
calendar date/time with no fraction or exactly six fractional digits, plus a
canonical whole-minute ±HH:MM offset. Exact existing offsets, including -04:00,
remain supported; the actual emitter remains datetime.now(UTC).isoformat().
Lexical validation precedes datetime parsing. Calendar validity and an exact
isoformat roundtrip precede freshness and range use. No endpoint is rounded,
floored or admitted with tolerance. Fractional or second-resolution timezone
offsets and submicrosecond timestamps fail closed.

The complete immutable input archive binds the original rejected V4 producer,
independent review, failures and exact separately bound Settings supplement.
The 276 journal bytes come from that supplemental archive; V4 never bound them.
Tests execute in a fresh isolated copy of the explicitly enumerated closed packet,
with filesystem audit guards preventing fallback reads from the live workspace.

Decimal raw-token parsing bounds token length and effective exponent before exact
construction with a private invalid-conversion context. It does no arithmetic,
rounding or context-dependent precision adjustment. Caller flags and traps remain
unchanged on successful and rejected documents. Original exact-nanosecond,
trailing-zero and exponent behavior is retained. Every V5 runtime-summary branch
uses a schema in the V5 namespace.

The input archive contains 2,393 explicitly enumerated source, input, tool and
historical evidence files (55,741,902 bytes). Its member tree is
`b572d93c66dfbf99846e9bcd66d9e625d5a614779183f15fc134fe1030b01c42`;
the archive is
`3b509aadf2b31314ec9fd910acb4fe3b3040505a446fff8f691bf765a599da7e`.
Before copying, V5 verified the original V4 handoff
`79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07`,
packet `4622a27a5e4c9dc9651b3eee6022e850dab1f55db3b48ac8f0daa4921b80e77a`,
and rejected review handoff
`93c6505ba122b532aafe3fdcd65a3a09273d046fafc37d633b9ec860dd503233`.
All 535 producer handoff members, 621 dependencies and 959 review members match
their explicit manifests. The 276-file supplement retains its original
1,190,150 bytes and tree
`c5c19c9aa0520f92f904f698823a90994e89166f3693df07ced052e9e38aeb68`.
The old closed replay's 7/25 repair and 12/37 V3 results, its missing-fixture
failures and the separate successful supplemental replay remain in the archive.
No claim is made about which unbound historical bytes V4 had previously read.

Only the selected `importer.py` and appended `join_support.py` adapter differ
from V4. The other 29 selected source files, including the actual Bridge,
durable Settings Session and TransactionStore implementation, remain byte-identical.
The accepted native source tree remains
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`;
the 55-member product tree remains
`e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`
and product archive remains
`0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`.
Original oracles, action budget, timings, auxiliary validator and observer V2 are
retained. The selected source manifest enumerates every composed source path.
`namespace-adaptation.patch` and `v4-to-v5-repair.patch` separate namespace changes
from repairs and added host verification infrastructure.

The final isolated host command is:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5/verify_host.py --attempt 3
```

Python 3.14.8 ran these retained sets from a fresh closed-packet copy:

| Control set | Result |
|---|---|
| Original producer controls | 111/111 |
| Original focused repair controls | 25/25 |
| Exact V3 reviewer controls | 37/37, including its 25 composition probes |
| V4 precision controls | 19/19, containing 35 adapter cases |
| Frozen actual-adapter precision cases | 8/8 |
| Historical exact reviewer | **32/33**, retained malformed direct-TransactionStore fixture failure |
| Frozen V4 independent controls | 36/36 |
| Focused V5 repair controls | 16/16, containing 82 adapter attempts |

The [isolated attempt receipt](../verification/apple-focus-reference-runtime-v5/host-attempt-3/receipt.json)
has SHA-256
`5a7ee1ce3fdd3919db239ce96775f9f604a3c5108e4f8e932869d1cacf017a73`.
It binds the exact closed source/input/tool archive, Python identity, inherited
compile revision label, command, outputs and cleanup. The revision label
`ba9ad4372f94463ba4d363cdfd76dd565c96413f` is inherited only; exact hashes define
this host work. No Git query or mutation occurred.

The 36 frozen V4 test bodies and assertions retain their meaning, with explicit
namespace/path adaptation. They retain 1,800 exact rational scalar cases, 800
genuine sub-nanosecond cases, 32 hostile Decimal profiles and 89 adapter attempts.
Schema 5 rejects two unsupported root timestamps before capture, so 82 attempts
mint a capture and call the actual derived runtime summary. Root approved a
replay-only helper adaptation for those two earlier rejections: the actual
`configure_root()` ValueError is saved, with timestamp data unchanged, and the
same error is raised inside the legacy helper's existing rejection boundary.
Schema/name rejections are raised immediately. The helper's complete original,
adapted source and exact diff are separately bound; no exception is fabricated
and no production validation is deferred. The legitimate -04:00 equivalence
control passes unchanged under the coordinated whole-minute-offset contract.

The new V5 controls directly test early root rejection, canonical/calendar
roundtrips, accepted UTC and exact offset forms, unsupported fractions and offset
seconds, freshness at zero and 300 seconds with ±1 microsecond boundaries, and
summary/run endpoints with ±1 ns boundaries. They exercise every explicit
no-capture/cleanup early return and runtime failure checks through the actual
adapter and summary. Caller Decimal flags are tested initially clear, all set
and individually set, with all traps enabled and disabled; exact success and
invalid exponent rejection leave flags, traps and precision unchanged. Missing,
changed and unlisted fixture controls fail closed and restore the isolated bytes.
The 82 adapter attempts include 60 actual derived summary calls; the other 22
reject at the root or official execution boundary. These are case counts within
the 16 controls, not additional test totals.

All failed attempts are preserved. The first binding command rejected an overly
strict handoff metadata equality before producing an archive; its source and
explicitly labeled reconstructed terminal description are retained. Host attempt
1 preserves the missed V4-to-V5 schema-string adaptation, parse-spy fixture setup
mistake and the two correctly early root rejections outside the old helper catch
boundary. Attempt 2 preserves the helper routing scope mistake that intercepted
the schema exception expected by frozen control 28. Attempt 3 narrows routing to
the actually raised canonical-timestamp error and passes every current control.
None of these harness failures is relabeled as a producer pass. The unchanged
historical malformed fixture remains rejected with its acceptance assertion
failing in every replay.

The parent audit boundary permits only four inspected hash-pinned Python
composition programs. Each child installs its guard before importing the actual
composition. All native process, service and network actions are forbidden.
File reads and directory scans outside the isolated tree and Python runtime are
rejected; no live workspace fallback glob can supply a missing fixture. All
tool returns, Settings requests, AX/PNG payloads and acknowledgments remain
synthetic host fixtures. No native input, screenshot, compiler, simulator,
emulator, device, UI or capture command is invoked. The frozen hosted
catalog/authority lane and separately interrupted worker transport V2 review are
not read, imported or executed.

The [frozen handoff](../verification/apple-focus-reference-runtime-v5/handoff.json)
binds source, immutable inputs, tool bytes, selected source closure, every attempt
and the full output archive. Verify it with:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-focus-reference-runtime-v5/freeze.py verify
```

Preparation never selects or dispatches native work. Future separately reviewed
dispatch requires a fresh `mixer.apple-focus-reference-root-selection.5`, a name
beginning `MixerFocusReferenceV5-` and fresh `native-run-v5-` output with its run
UUID; V3/V4 selections and outputs cannot be adopted. Root selection and
independent V5 review remain pending. Owned isolated scratch is absent after
every attempt, all 2,393 input bindings are unchanged after controls, and no
other project's process or data is touched.

Native execution, the original authored-first failure, full keyboard/comparator
coverage, immutable published FieldLog packages from a separate repository,
physical-phone matrix, signing, store, operational and accountable-reviewer gates
remain open. No development or GA gate is promoted by this packet.
