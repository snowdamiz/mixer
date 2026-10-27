# Exact source146 leaf and shell work component proposal

This frozen packet derives a finite source-specific component interface. It does
not select a host grant, execute the loaded fixture, or qualify its writer. The
actual146 distribution is `690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`,
with unchanged host11 `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
It freshly checks four frozen packet seals and every actual146 source member.
Only retained production metadata/MIR and separately bound actual146 layouts are
read; no frozen script is run or imported.

The owned boundary begins at `run_one_loaded_fixture_v1` in the actual composed
`initial_profile_v1.rs:659`. It includes that function and these concrete source
bodies, each at most once through its consuming call graph:

| Body | Conservative written source actions |
| --- | ---: |
| `run_one_loaded_fixture_v1` | 186041 |
| `SelectedValidatedProfileV1::into_snapshot_scope_v1` | 18026 |
| `SelectedValidatedProfileV1::into_adoption_body_v1` | 10242 |
| `SelectedSnapshotBodyV1::into_adoption_body_v1` | 2095 |
| `RuntimeControl::adopt_snapshot_body_v1` | 81665 |
| `SnapshotScopeV1::construct_v1` | 105396 |
| `SnapshotRunV1::outer_v1` | 19293 |
| `SnapshotRunV1::finish_v1` | 216479 |

The fixed scalar-leaf source surface is **639237** abstract action units. Its
unit is separately specified in `cost-interface.json` and is not CPU time. Every
written operation is conservatively charged two fetch/store actions for each
mentioned role's complete inline scalar shape and reachable finite typed
pointees, plus explicit control/projection actions. Moves, aliases, temporary
places, StorageLive/Dead, return-place transfers, cleanup blocks and alternative
variants receive no liveness discount. Each acyclic function charges all its
blocks once, an upper envelope over every enumerated path; this does not claim
all blocks execute together. There are 205 typed roles, 598 written MIR operations
and 13827 finite terminal paths, including unwind/termination paths.

The separately counted native occurrence dimension currently has **118660**
known bytes and 53 required actual146 `sizeof` terms with explicit coefficients.
The source and native dimensions each also require `2188 * L_str`, where `L_str`
is a positive reviewed finite bound on each encountered unsized string backing.
The combined evaluator therefore adds `4376 * L_str`; it never silently treats
that backing as the width of its reference. Typed claims alone contribute 256
pointee scalar leaves behind the eight-byte reference. Scope-borrow aggregates
also carry the concrete control/cache/optional-WASI pointee surfaces. Native
layout types, requested backing, dynamic owner payloads, standard operations and
compiler lowering are separate terms. A pointer measurement is never aggregate
transfer or destructor coverage. The historical leaf30 inventory and 34885
partial price are not imported as acceptance or as native layout measurements.

There are **33 mandatory positive callee/drop/backing cuts**. They include exact
called source methods, standard generic calls, typed drop operands, native and
resource backing, and an explicit split of `adopt_body_core_v1` before its fixed
counter store at actual146 `control.rs:716` versus that store and its following
body. The latter core is intentionally outside the eight-body surface. This
packet prices neither side of that call nor any actual payload destructor body.
Every such term remains required and nonzero, including exceptional cleanup and
returned diagnostic destruction. The sibling payload lane owns actual payload
work; the written shell operand transfers in this packet remain separately
attributed. P1 setup/loader, P2 caller arguments and P5 returned wrapper/payload
work are outside this boundary.

No accepted 451814442 product price, historical authority delta, unentered
callee, or host code is used as a discount. The core boundary map records the
exact function hash and pre-store slice hash. A later composition may only
subtract overlap after proving the exact source/function/callee/action cut and
independently accepting its price. This packet conservatively keeps the full
constructor surface. Product limits, WorkAuditPending, retained construction,
unknown root policy, complete P0 and all six child components remain unchanged.
No healthy cleanup, actual executable/session/fixture binding, native/OTA or GA
claim follows.

The 24 pure control methods pass, including 435 required-input negative cases
for omitted/zero/negative/boolean/noninteger layout/callee/unsized terms. They
also test checked-u64 overflow, cyclic or incomplete control graphs, absent or
ambiguous MIR boundaries, unknown source types, complete typed pointees and
source/native separation. Synthetic positive evaluator values exercise only the
interface; they are not selected real prices. The first test run had one checker
failure caused by directly comparing Python tuple pairs with their equivalent
JSON arrays. Its exact command/source/output and the correction are retained
under `attempts/01-json-roundtrip-comparison`; it was not a product finding.
Earlier fail-closed exploratory scanner findings are summarized separately.

Reproduce before freezing with `python3 .../run_checks.py`. Once frozen, run
`python3 .../verify.py` for the read-only seal and deterministic pure checks.
`derive.py` and the collector refuse to overwrite a frozen packet. All commands,
Python version/executable hash, tested own-source hashes, revision, immutable
source tree, stdout/stderr and scope are retained. No new compiler, loader,
VM/cache/scope/constructor/writer, fixture or actual destructor runtime is used.
No UI, capture, native simulator/emulator or global process inventory is used.
No disposable native instance or scratch directory was created; the Python
children were waited and other projects' processes were untouched.
