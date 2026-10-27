# Existing-owner provider work/storage candidate

This is a **producer candidate requiring fresh independent review**. Its source
boundary is the root-accepted, explicitly unqualified existing-owner provider
tree `acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d`.
Only this verification directory is authored. Canonical code, selectors, root
policy, accounts, input acquisition and operational authority are unchanged.

`candidate.json`, `source-typed-MIR-map.json`, `phase-roster.json`,
`required-input-contracts.json`, and `layouts.json` are deterministically derived
by `derive.py`. The full source146 roster is verified against its frozen origin
files; both accepted provider packets and the inherited outer/storage models are
byte-bound. The root's mandatory complete 6,006-construct correspondence includes
1,785 standalone constants. That proof transports the previous outer costs only
through the accepted scoped-binding source boundary. It does not price this new
provider or grant authority.

## Derived envelope

All eleven new production MIR constructs are mapped: one main function, its
actual `and_then` closure, two promoted constants, and seven standalone constants.
There are 193 typed/constant roles: 171 main, 11 closure, four promoted and seven
standalone. All 565 written MIR operations, including storage annotations,
constructor/move/copy/return/error operands and index/unwind endings, are retained.
The source ranges bound twelve identity iterations and five path iterations.
Their `next` headers execute at most thirteen and six times. The actual authored
closure executes at most five times, sequentially; its work is charged five
times, with its one set of logical slots retained throughout P0.

The new source-work interface is:

```
276580 + 1324 * B
B = max(12 actual identity lengths,
        5 actual native path body lengths,
        5 separately retained path body lengths)
```

This uses the inherited logical source/typed aggregate/finite-end unit plus
native typed-byte allowances. `B` is derived from actual declared bodies and is
not a selected maximum. The calculation prices the new authored caller and
closure surfaces. It does not invent a private standard-library, compiler,
panic, allocator, kernel or CPU price.

Fourteen new standard-library interface terms remain strict positive inputs:

| Interface | Conservative invocation cap |
| --- | ---: |
| Range into_iter | 2 |
| Range next | 19 |
| slice len | 33 |
| usize checked_add | 22 |
| Option ok_or with shape refusal | 17 |
| Result Try branch | 17 |
| candidate Result from_residual | 2 |
| digest array inequality | 1 |
| Path as_os_str | 5 |
| OsStrExt as_bytes | 5 |
| slice is_empty | 5 |
| slice contains u8 | 5 |
| slice-reference inequality | 5 |
| Option and_then, excluding the authored callback | 5 |

These are full required callee-interface inputs in this candidate, even where
an earlier narrowly selected interface might eventually apply. No earlier
interface is silently generalized. The authored callback's own work is already
charged separately. Actual prepaid acquisition and the future provider
caller/launcher each retain a positive work term. All ten inherited residual
terms, including the **unselected** `67424 * L_str`, remain intact. Thus the
conditional fixed whole expression becomes `895084428326233374`, followed by
`1324 * B`, those ten inherited terms, the fourteen new terms with the caps above,
and the two new upstream work terms. This is not a whole quote or selected bound.

Every written logical slot is conservatively reserved through all fifteen
inherited phases, until final outer-result consumption. Native typed slots total
8,344 bytes. One additional external caller Result place contributes 1,352,
bringing the P0 addition to 9,696 and the prior fixed P0 from 292,037 to 301,733.
This includes all written parameter, moved aggregate, constructor, return and
closure slots as distinct source places. It claims no physical stack or alias
layout. Unwritten future caller/input-staging storage remains within the
mandatory positive future-root-inline input; no invented extra staging container
is added.

The original 1,168-byte full binding remains in the inherited P0 base. All twelve
full preimage backing allocations, five native Path allocations, five separately
retained byte-body allocations, original diagnostics, future root inline/backing,
native operands, original Error owners and complete payload/carrier/destructor
temporary backing remain mandatory. They are not duplicated merely because the
same borrowed container moves into a new slot. Conversely, equal contents or
pointers supply no backing credit. `logical_input_backing_bytes` describes the
sum of the twenty-two actual lengths; it is neither another allocation nor an
allocator-capacity bound. The six inherited child storage components are reused
unchanged. None/refusal/unwind supplies no refund; normal release still requires
actual original payload/carrier destruction returning the existing Some token.

## Compiler custody and host verification

The original ten named layout queries supplied twenty observations in the
root-accepted provider packet (ten size/alignment pairs). Its anonymous closure
layout was missing. Root approved one production opt0 LLVM-IR/metadata/MIR query
with an inert exact HRTB function pointer, forcing the unchanged function and its
actual closure. The final plan is `compiler-plan.json`, SHA256
`63b3274f5e90218cf2d58f09d67aabbeff4e53c4c7a1c2195aca429a4be193bc`.
The original proposal and runner are preserved under
`attempts/initial-compiler-plan/`; root's sole adjustment changed the anticipated
stdout/stderr cap from 4 MiB to 16 MiB. The 55-second limit, source, cfg, compiler,
target and no-retry/no-link/no-runtime boundaries were unchanged.

The query succeeded once in 4.35 seconds with rustc 1.99.0
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, compiler SHA256
`dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0`.
It observed all thirty-six requested named dimensions and the **actual closure
aggregate at 16 bytes, alignment 8**, at the unchanged production 1185:27 span.
Its actual MIR fields are `native_path_bodies: &[&[u8]; 5]` and `position: &usize`.
No field-size sum substitutes for the aggregate observation. The compiler's
opaque `end padding:16 bytes` detail is retained verbatim without interpreting
the captures as padding. All eleven provider constructs match the previous
compiler MIR after only comments and exact scratch-path identities normalize.
The complete new MIR and LLVM are retained as deterministic gzip files.

The compiler child was reaped; its owned process group is absent and its owned
scratch is removed. No linked executable, Rust test, native runtime, simulator,
emulator, phone, UI automation or capture ran. Other projects' processes were
not inventoried or touched. Physical/native checks remain pending under pause.

`model.py` has two distinct scopes. `describe()` mirrors only the Rust provider's
shape, selected-source length/claim, no-empty/no-NUL, path equality and checked
u64 sums. It deliberately accepts forged content carrying the selected source
claim, demonstrating that it cannot authenticate inputs. `storage()` and `work()`
add the inherited full-preimage/backing and loader geometry conditions, with an
explicit source-only conversion into the unchanged frozen evaluator. Those
additional caps are not claimed as provider enforcement. Positive byte/work
labels and arithmetic are not proof of actual acquisition, capacity, ownership,
identity correspondence or funding.

The latest retained host run passes 29 test methods. Controls independently
reconstruct all 565 operation prices at three body sizes (1,695 equalities), all
weighted per-function totals and role endings, both loop/callback multiplicities,
all fifteen storage phases, all old/new term omissions and invalid source/units,
each identity/path/backing omission, overflow, non-UTF8 paths, aliasing, digest
forgery, source-only cap boundaries, unknown calls/operands/constants and mutated
MIR constructs/loop edges. Two initial fail-closed host constant-namespace parser
failures are preserved under `attempts/derive-001` and `derive-002`; the compiler
was not retried. These are producer controls, not an independent acceptance.

Read-only verification after freeze:

```
python3 -B verification/swift-guarded-snapshot-owned-provider-work-storage/check_packet.py
python3 -B verification/swift-guarded-snapshot-owned-provider-work-storage/derive.py --check
```

All six upstream requirements and all three original selectors remain Pending.
Actual backing maxima, prepaid child-side acquisition and ownership/admission,
diagnostic and identity/path correspondence, root policy/quote/funding,
executable/build/session closure, genuine loader/writer/destructor execution and
healthy cleanup remain required. No L_str selection, operational grant, native
qualification, separately published-package FieldLog release, OTA or GA follows
from this candidate.
