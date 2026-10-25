# Apple reference-first runtime V4 independent review

**Rejected for dispatch.** The Decimal tuple repair survives the retained controls
and new independent exact-time probes, but root ISO timestamps still truncate
precision, and the frozen closure omits historical journal inputs needed by the
composition controls. Two smaller issues affect ambient Decimal flags and the
schema of incomplete runtime reports. No producer file was edited.

This is a host-only review of the frozen V4 packet. It grants no native runtime,
compiler, input delivery, device, keyboard, carrier, complete-case or GA credit.
Physical phones remain disconnected and deferred. A repaired, frozen packet needs
independent review and a fresh root selection before any separate dispatch.

## Exact reviewed identity

The reviewer independently verified these bytes before copying or executing any
control:

| Input | SHA-256 |
|---|---|
| V4 handoff | `79a8a2d5070b1f9466831089be0f2f89d1e67d3785c707879414ea2edac9ca07` |
| V4 packet | `4622a27a5e4c9dc9651b3eee6022e850dab1f55db3b48ac8f0daa4921b80e77a` |
| V4 host-attempt-2 receipt | `771d70983473916cc8004d2c3a4893b2ce82bfc0e0a992ce657cd853fa5e35c3` |
| 535 handoff members | `1026b48423fc2b98beb46a5d21144de6cd8960881658c7c8ba73847a9add3c0d` |
| 621 frozen dependencies | `30e511b5622426f8288595da7613e829e50eba34046d8351186a7d415067cca4` |
| Independent combined closure | `ed66b22c833ce4777e0a7ea9ac759011baea0fde185fc81b71ffa6cdd4c73309` |

The complete explicit closure, including six external tool-file bindings, was
copied into owned scratch before replay. Tool files were hashed as data. No native
tool was invoked. The 31-member selected archive, 39-member accepted source tree
`696bfdd8a31be7b4d9ba49f57783625c7edbb75c126bb4696e31acc5aa0f238a`,
product archive `0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8`
and 55-member product tree
`e3d60e7c69dcbe6e75e7089840b62dd4dd475f4a9db4fe87465543f822b39e20`
were independently checked against their complete archive member manifests.
The inherited revision label is `ba9ad4372f94463ba4d363cdfd76dd565c96413f`;
exact hashes define the reviewed source. No Git query or mutation occurred.

V3 and V4 selected archives have the same 31 paths. Only `importer.py` and the
appended `join_support.py` adapter differ; the other 29 files are byte-identical.
The actual Bridge, Session, TransactionStore, auxiliary validator, classifier,
observer V2, original oracles, action budget, timings and compiled products retain
their bound bytes. Exact reviewed sources and producer identity files are retained
under `verification/apple-focus-reference-runtime-v4-independent-review/frozen-producer/`.

## Findings

### F1 — P1: root wall time silently loses fractional precision

`verification/apple-focus-reference-runtime-v4/importer.py:62-66` converts the
original root string with `datetime.fromisoformat()`, whose result retains only
microseconds. `validate_root()` repeats that conversion at lines 134-138 for
freshness, and `official_methods()` uses the truncated endpoint at lines 198-204.
Neither function restricts the accepted root string to representable precision.

The actual derived adapter and `runtime_summary()` accept this complete synthetic
execution as `one-strict-original-verdict-passed`, with provenance accepted and
key count 1:

```text
selectedAtUTC:           2026-10-25T02:00:01.000000001+00:00
true root endpoint:      1792893601000000001 ns
datetime_ns(root):       1792893601000000000 ns
raw summary startTime:   1792893601.0
summary start endpoint:  1792893601000000000 ns
```

The run begins 1 ns before its actual selected root. A root string ending in
`.000000000000000000000000001+00:00` also admits a summary that predates the
original root, instead of treating unrepresentable precision as incomplete.
With a frozen clock, `validate_root(fresh=True)` additionally accepts a selection
1 ns in the future after truncating it to the current microsecond.

Failing independent controls are `test_09_root_nanosecond_future_of_summary_must_reject`,
`test_10_root_subnanosecond_tail_must_reject` and
`test_11_fresh_root_future_by_one_ns_must_reject`. Complete raw inputs, capture
exports and results are retained in `independent-attempt-2/root-nanosecond-early-summary/`
and `independent-attempt-2/root-subnanosecond-early-summary/`.

Enforce a canonical, exactly representable root timestamp before parsing, or
retain an exact original endpoint and reject unsupported precision. Apply the
same rule to freshness and selected-run range checks, including timezone offset
precision. Do not floor or round an endpoint to admit it.

### F2 — P1: the frozen host dependency closure omits 276 Settings journals

`verification/apple-focus-reference-runtime-v4/test_repair.py:33-35` reads
`verification/apple-focus-diagnostic-runtime-v1/runtime/captures/0000-settings-*.json`.
The exact frozen V3 composition program performs the same read at
`verification/apple-focus-reference-runtime-v3-independent-review/run_review.py:60-65`.
None of the 276 files is a V4 handoff member or frozen dependency.

The first replay used only the independently copied explicit closure. The 111
producer controls, 19 precision controls/35 adapter cases and eight frozen
adapter cases passed. The focused suite passed 7/25; 18 composition controls
failed on `journals[0]` with `IndexError`. The V3 replay passed 12/37, with all
25 composition probes failing before their assertions. The historical suite
remained 32/33 with its existing malformed-fixture failure.

The reviewer then separately bound and copied the exact referenced glob: 276
historical files, 1,190,150 bytes, tree SHA-256
`c5c19c9aa0520f92f904f698823a90994e89166f3693df07ced052e9e38aeb68`.
The supplemental archive and original file identities are retained. Its tree is
reviewer evidence from the current historical files; V4 did not bind those bytes
when its own evidence was frozen. Adding these files makes all retained suites
replay with their advertised results, but cannot establish which bytes the
producer's earlier execution read.

Failing independent control:
`test_36_frozen_closure_covers_referenced_settings_journals`.
Bind a complete immutable Settings journal fixture in the producer dependency
manifest, enumerate it explicitly, and replay from a copy of the closed packet.
Preserve both the failed closed replay and the supplemental replay.

### F3 — P2: invalid exact tokens mutate the caller's Decimal flags

`verification/apple-focus-reference-runtime-v4/importer.py:106-109` constructs
`Decimal(token)` using the ambient context for invalid conversion. Through the
actual adapter and derived summary path, the raw token
`0e9999999999999999999` rejects as incomplete evidence with unknown key count,
but sets the caller's `InvalidOperation` flag even when the exception is caught
and reported as `ValueError`. The caller's previously clear signal state changes.

Failing independent control:
`test_06_unrepresentable_raw_exponent_does_not_mutate_ambient_flags`.
Retained evidence includes `independent-attempt-2/invalid-exponent-context-flags.json`
and its complete adapter input/result capture. Valid tuple conversions preserve
all tested contexts and pre-existing flags. Reject unsupported exponent syntax
before context-sensitive construction, or isolate construction from the caller's
context, while continuing to reject unrepresentable tokens and preserving flags.

### F4 — P2: incomplete V4 runtime reports retain the V3 schema

`verification/apple-focus-reference-runtime-v4/adapter.py:114-116` initializes
`schema: mixer.apple-focus-reference-runtime.3` and returns it when official
capture or cleanup is unavailable. The exact V4 derived adapter therefore emits
a V3-labelled runtime report on its incomplete path. This defeats the requested
V4 output namespace separation for that path.

Failing independent control: `test_29_no_capture_runtime_output_uses_v4_schema`.
The exact output is `independent-attempt-2/no-capture-runtime-summary.json`.
Give the incomplete/failure report the V4 schema and test every early-return
path. V3 root schema/name rejection and the `native-run-v4-` path guard otherwise
remain intact; no successful V3 execution adoption was observed.

## Executed evidence

Every command used Python 3.14.8 via
`/opt/homebrew/opt/python@3.14/bin/python3.14 -B`. Commands, tool identity,
source/output hashes and scope are retained in the receipts and frozen manifest.

```sh
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/bind_inputs.py
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/run_replays.py
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/supplement_inputs.py
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/run_replays.py --attempt 3
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/run_independent.py --attempt 2
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/collect_static.py
python3.14 -B verification/apple-focus-reference-runtime-v4-independent-review/finish_review.py
```

The supplemental replay (`replay-attempt-3`) retains these exact results:

| Set | Result |
|---|---|
| Retained producer controls | 111/111 |
| Focused repair controls | 25/25 |
| Exact V3 reviewer controls | 37/37 |
| Composition subset within those 37 | 25/25 |
| V4 precision controls | 19/19, containing 35 adapter cases |
| Frozen V3 actual-adapter precision cases | 8/8 |
| Historical exact reviewer | **32/33**, one retained malformed direct-TransactionStore fixture failure |

The historical control bodies and assertions remain unchanged. The malformed
direct-TransactionStore record remains rejected; no validator whitelist or
acceptance assertion was weakened. Its failure is not a new precision failure
and is not represented as 33 passing controls.

The final independent suite is **30/36**, with six failed assertions grouped into
the four findings above, zero errors and zero skips. It contains 89 actual adapter
attempts; 84 mint the capture and call the actual derived `runtime_summary()`.
Five invalid summary/root cases reject before capture. These are case counts
inside the 36 controls. They are not additional test totals. Coverage includes
1,800 independent exact rational scalar cases, 800 genuine sub-nanosecond cases,
32 hostile precision/rounding profiles with every trap enabled and tiny exponent
ranges, pre-existing signal flags, signed extreme zeroes, bounded coefficient/
result/token/exponent work, binary-float collisions, exact attachment order,
baseline lower bounds, original premise/witness upper bounds, and changed and
unchanged after files. Changed after data at the later witness remains eligible;
before data 1 ns after the original premise and after data 1 ns after the witness
remain rejected.

The V3 deep-tail Decimal-rounding failure is repaired for those tested decimal
documents: exact nanoseconds with trailing zeroes and exponent notation accept;
genuine sub-nanosecond endpoints reject without count/fault inference. Integer
construction and powers follow coefficient/result caps; exponent magnitude does
not drive allocation or iteration. No timing tolerance or global precision change
was introduced by the reviewer.

All failed attempts are retained. `replay-attempt-2` repeats the missing-input
failure after a reviewer supplemental-binding attempt incorrectly required native
historical journals to have one link; the native journals have two links. Its
wrapper then failed while writing a receipt for the absent supplemental manifest;
underlying control receipts/logs survive. The corrected data snapshot records
original link counts and creates ordinary copied files. `independent-attempt-1`
also retains one reviewer raw-token replacement collision in test 27. Replacing
all original tokens with unique placeholders first repaired that harness issue;
the corrected test passes in attempt 2. These reviewer mistakes are not producer
findings, and no failed evidence was overwritten or relabelled.

## Boundary and cleanup

Parent audit guards allowed only the four inspected, hash-pinned Python
composition programs inside owned scratch. Each child installed a review guard
before importing composition. All other subprocess, native, service and network
actions were forbidden. The independent exact-time suite forbade every subprocess
and network action. Its tool returns, app observations, Settings replays and
acknowledgments were host fixtures. The frozen hosted catalog/authority lane and
the separately interrupted hosted worker transport V2 review were neither read,
imported nor executed.

All 535 members and 621 dependencies were rehashed after the controls. The
supplemental journal bytes were rechecked. Owned scratch was removed in the final
cleanup, including the scratch from failed attempts; other projects were
untouched. `cleanup.json` and the final independent handoff bind that result.
No compiler, simulator/emulator/device query, native execution, UI/screen capture,
service, signing, publication, customer message, credential action or shared
tracking edit occurred. All native and GA acceptance fields remain false.
