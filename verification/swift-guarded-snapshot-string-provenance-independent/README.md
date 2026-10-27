Independent review of source146 string provenance

Decision: return frozen candidate b228f62a0751e6d1b45e27edabe500cc5e52449db1d33ee59abca0f695b6fa2f
for correction. Root owns selection. This review accepts no L_str, source
closure, whole-host bound, policy, account, product execution, OTA or GA grant.

Custody passes: all 114 candidate members / 6,305,257 bytes and 315 declared
input files match, including the exact source146 tree, host11 tree, compiler
receipt and retained 76,655,228-byte MIR. The root release and remaining-work
amendment hashes match the supplied pins. Rehashing did not execute a compiler.

audit.py independently parses the retained MIR, resolves selected authored
methods and concrete policies, expands compiler closure sites and named typed
function-item callbacks, and computes a fixed point. It imports no producer
analysis. Only after that fixed point does it load graph.json for comparison.
The full recovered graph is retained in typed-graph.json, with body digests,
calls, incoming ports, assignments, carrier operations and external sites.

The reconstruction covers 525 bodies and 1,908 edges. Every one of the
producer's 519 body hashes and 1,879 edges is reproduced. It adds six bodies
and 29 edges: 28 named callback edges at 22 sites and one transitive call.
The 1,127 external targets at 3,209 sites remain unchanged. No indirect call
or unresolved compiler allocation identifier was observed in this frozen route.

The missing bodies are f1605 AccountedWasi::snapshot_configuration_v2,
f1697 WasiContext::snapshot_configuration_v2, f1899/f1900 enum Runtime
constructors and f1927/f1928 enum Stop constructors. Full omitted MIR bodies
are retained separately. Configuration bodies copy numeric budget/grant
fields. Enum bodies move an existing failure/stop into its wrapper. Another
15 named callback edges invoke AccountedWasi::usage, whose body was otherwise
already reached. These additions create no new string origin, but the
candidate's claim of a complete callback graph is inaccurate.

The producer also misses two primitive str assignments because local types
are parsed only at exactly four spaces of indentation. The independent census
has 80 assignments: 24 literals, 54 preserved references and two calls to the
expanded policy_identity body. The missing f0279::_35 at MIR body line 256
projects a tuple's str field; f1035::_29 at line 203 projects the cleanup
invariant/code tuple. Both preserve references. All nine direct str ports have
incoming calls in the reconstructed graph. Carrier token census remains 1,735.
missing-coverage.json contains exact sites, names, statements and edges.

All 1,958 compiler allocation occurrences (1,464 unique identifiers) are
covered, including promotions/global aggregates/compile-time option_env.
Their maximum is 5,080 bytes. All 3,189 cooked str occurrences (1,397 distinct
values) independently decode to a maximum UTF-8 extent of 92. Thus 92 alone is
insufficient for the proposed general constant-origin overcoverage. The
5,080 envelope remains supported for that frozen origin pool. Its value is
not a theorem about arbitrary static strings. The independently recovered
additions conserve values, but they must be incorporated into the producer's
proof and binder before root selection.

Source semantic excerpts and hashes are in source-semantic-review.json.
The exact route consumes the unmodified loader-produced proof, creates fresh
cancellation/control with first_failure=None, fixes Swift policy and closed
specializations, and admits no incoming failure/Fault/code/custom callback or
intervening mutation. Reader/Meter/BodyState errors forward supplied codes.
Fault and first-failure latching preserve references; Swift failure mapping
copies raw.code; return, error, retirement and enum wrappers preserve values.
Public SwiftRunFailure.code and lower APIs permit caller strings of arbitrary
length on other routes. Actual Path/OsStr and io::Error backing stay outside
L_str in separate native allowances. The present quote refusal is not used
to make the latent prepaid-route bound vacuous.

adverse.py is independently authored and deliberately retains six failures
against the frozen producer: nested-scope local omission, named callback
omission, unknown reference-trait producer, unknown generic-trait producer,
unknown comparison-named trait producer, and unreviewed std namespace using
an allowed method basename. These are parser/checker tests, not compiled
product fixtures. UTF-8 adverse values and the exact existing omissions
controls pass. Actual encoded multibyte lengths are checked; neither lifetime
nor pointer width supplies a length assumption. The reusable classifier
findings are separate from the actual frozen-route coverage defects.

The producer's original 14 tests pass and derive.py --check reproduces the
sealed packet. They do not cover these findings. Original failed attempts 006
and 007 remain pinned in the producer packet. Our commands/ receipts retain
the eight-test run with six failures, the independent parser's initial failed
attempt and subsequent refinements, and the successful original test/check
runs. A recorder allocation race prevented one requested child from starting;
recorder-allocation-failure.json records it separately. It is not counted as
a derivation or producer result. Script snapshots preserve each revision.

correction-contract.json specifies deterministic repairs and expected counts
for a new separately owned/frozen packet. Product source and this candidate
must remain frozen. Root should release the corrected packet before renewed
independent review. No scalar bound, different caller, unknown trait, or
namespace basename may silently close a string-origin frontier.

The checked substitutions are 4,236,953+4,376*5,080=26,467,033 and
67,424*5,080=342,513,920. They select no whole-host expression or allowance.
The remaining 14-interface amendment is context only. Actual P0/root/caller,
fixture/build/compiler/session/executable selection, complete binary
correspondence, runtime/healthy cleanup, immutable external FieldLog, native,
device, OTA and GA remain pending. No compiler/runtime, native instance,
UI automation, capture, global process inventory, Git or root-metadata action
was performed. Only this independent packet was written.

Recorded commands use the owned recorder, never the producer's run.py:

    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance-independent/custody.py
    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance-independent/audit.py
    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance-independent/adverse.py
    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance/test_provenance.py
    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance/derive.py --check
    PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-string-provenance-independent/run.py verification/swift-guarded-snapshot-string-provenance-independent/report.py

After sealing, replay read-only checks using a new external owned recorder;
do not add attempts or regenerate this frozen independent packet in place.
