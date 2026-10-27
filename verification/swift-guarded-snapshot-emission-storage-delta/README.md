# Conditional emission-helper storage and caller delta

This is an isolated, compiler-only proposal to replace the existing refusal
wrapper body with direct tail delegation to the accepted pure arithmetic helper.
The actual authority225/source144 tree575b55, accepted unused helper packet,
canonical files and Git state are unchanged. No product function, writer, encoder,
VM, loader, native application or test binary executes here. `WorkAuditPending`
remains in the actual source.

The helper has **39 concrete MIR places totaling18,816 logical source bytes**.
Production and `cfg(test)` measurements agree for all ten requested real types
on rustc1.99.0/aarch64-apple-darwin. `roles.json` gives each occurrence its own
function/local identity, exact source span, source member SHA, MIR declaration,
uses and both actual compiler layouts. These are reservations for conservative
source occurrences under the existing owner convention, not physical stack,
ABI overlap, peak resident memory or target-device measurements.

| Actual helper places | Occurrences | Bytes |
| --- | ---: | ---: |
| Borrowed shape parameter | 1 | 8 |
| u64 locals, field reads, success payloads and moved scalar operands | 11 | 88 |
| Checked Option carriers | 4 | 64 |
| Eager Arithmetic error temporaries | 4 | 4384 |
| Result carriers including function return | 4 | 4384 |
| `?` ControlFlow carriers | 3 | 3288 |
| `?` residual bindings and forwarding temporaries | 6 | 6576 |
| Discriminant temporaries | 3 | 24 |
| Never-type places | 3 | 0 |
| Total | 39 | 18816 |

`AError`, `Result<u64,AError>`, the residual Result and ControlFlow are each1096
bytes, alignment8. Eager `Arithmetic` uses the complete real error representation
even though that variant has no large payload. Option<u64> is16 bytes; borrowed
shape and u64 are8. The existing104-byte shape is borrowed, with two actual scalar
field reads. Three distinct named locals, three success payloads and three other
scalar operand places remain explicit. Loops do not multiply storage; this
helper has none. Standard-library primitive implementation interiors are outside
the same product-source occurrence convention used by the frozen owner recipe.

## Exact wrapper and caller reconciliation

The proposed source is exactly:

```rust
fn proposed_emission_work_v1(shape:&SnapshotShapeV1)->Result<u64,AError>{
    emission_bound_v1::checked_snapshot_emission_bound_v1(shape)
}
```

The wrapper's baseline `_0` Result1096 and `_1` borrowed parameter8 retain their
same function/position/type identities. Only baseline
`owner::proposed_emission_work_v1::_2`, the actual `AError::WorkAuditPending`
temporary1096, is removed. Proposed wrapper `_2` is a new, actual8-byte compiler
reborrow. Thus the wrapper changes from2200 to1112 bytes, and the separate helper
adds18816:

```
net selected-unconditional addition =18816 +8 -1096 =17728
conditional S =941467 -1096 +18816 +8 =959195
```

`wrapper-delta.json` binds that specific removal and both retained slots.
`preserved-begin-roles.json` preserves all131 actual begin/closure places,
77,098 bytes. Fresh production and test MIR are structurally identical to the
frozen base after removing only source spans/line movement. In particular the
ten evaluator boundary places `_47` through `_56` retain the emission binding,
ControlFlow, call Result, two shape references, discriminant, two residual
places, never place and success payload. Actual caller return/tuple/phase/error
and cleanup storage stays in the baseline; no return Result is subtracted as
an alleged physical alias. No new Result temporary is invented for the direct
tail call: it writes the wrapper's existing `_0`.

All new places must be funded in **S at initial selected admission**, before
the evaluator, its computed work debit and the existing phase-storage commit.
Assigning these places to A at commit would be too late. This packet changes no
reservation. `checked-additive-recipe.rs` is a const-only conditional review
artifact with one checked add per helper occurrence, an identity-bound checked
subtraction for the old refusal, and checked outer folds. It has no runtime
functions or placeholder storage arrays.

The base owner recipe is **frozen and unaccepted**. Its producer values C77144,
S941467, A430175 and H81327 are retained conditionally; C/A/H do not change.
Root separately reports a source-identity defect in357 inherited aliases, where
temporary text/type pooling crosses different control receiver call sites. That
active review packet was not read. This delta does not consume its alias map:
its two reuse identities are local to this exact wrapper, and caller reuse is
checked against complete function MIR. The defect and pending base acceptance
remain explicit; these conditional totals do not acquire acceptance here.

## Work attribution

The accepted convention makes literals and bound local operands free and prices
each repository function's entry/return at2. The old wrapper is explicitly3
in the accepted writer ledger: entry/return2 plus the refusal carrier1.
The new bare-`shape` tail wrapper costs2. Its compiler-generated reborrow creates
real storage but no explicit source borrow or new source binding. A separate
call-boundary action would duplicate the helper's already counted entry/return.

The accepted helper29 remains its own obligation. Proposed evaluator work is
therefore2+29=31, versus old3: **net evaluator delta+28**. The existing begin
caller's `?` inspection/payload2 and binding1 remain counted once. This matched
evaluator delta is not a work bound for the entire operational change: replacing
the refusal would allow later begin/admitted branches to run.

`work-attribution.json` binds the source convention and corrected ledger. The
accepted emission expression remains19537+299377B+32E. It includes the transfer
initializer4096 once; future-begin7930 already names that same occurrence.
Combining interfaces must attribute one initializer, for example
`(7930-4096)+31+emission`, while retaining the separately accepted earlier
authority19 and all shell, inherited, caller, stop, cleanup and F1 lifetime
obligations. Planning16384 and ExecutionWork1,000,000,000 stay unchanged; this
packet does not prove a complete planning floor or select operational work.

## Compiler and integrity evidence

All eleven compiler expectations are met: ten successful compiler commands and
one deliberate constant-overflow E0080 refusal. Four initial source/layout
commands are followed by four final repetitions with full coordinator snapshots;
two final const recipe contexts pass and one overflow mutation fails. Every
actual compiled source roster is reconstructed by exact path/byte/SHA, including
the ten scalar layout-measurement tuples and never-type feature seam. Those
tuples measure actual types and are not modeled product owners or budget arrays.
No LLVM/MIR or metadata artifact is executed. Real compiler versions, full argv,
environment digests, exact source preimages, stdout/stderr and artifact hashes
are retained per command. The seven final compiler commands also retain the
exact coordinator source; the four initial commands retain its checksum plus
complete actual product-source and command preimages.

All137 finite integrity controls pass, including omitted/duplicated places,
full eager-error storage, residual storage, foreign source spans, invented
multipliers, late A funding, wrong return/caller subtraction, actual layouts,
unchanged caller bodies, source preimages, command/environment digests and u64
last-fit/overflow/underflow boundaries. No arithmetic runtime reexecution is
claimed; accepted helper tests are inherited evidence only.

One checker authoring failure is preserved in `attempt-history/`: reconstructed
member lists were sorted as full strings, while actual manifests use Path
component ordering. Every per-path byte and hash already matched. The checker
was repaired to use the captured ordering; no compiled source changed. An early
read-only filename search also referenced a nonexistent authority-work README
and returned2; it changed nothing and is recorded as an authoring observation.
The original provisional forwarding-action idea was resolved against the bound
operand convention before final controls; no runtime pricing was selected.

Each compiler has an owned process group,55-second limit, reaped child and
confirmed absent group. Every owned scratch tree and generated binary/MIR/LLVM
artifact was removed after evidence extraction; cleanup receipts retain their
pre-removal hashes. Only owned resources were inspected. No global process
inventory, native/device/simulator/emulator run, UI/capture, forbidden hosted
harness, authority driver, rejected worker or stopped Android experiment was
inspected or executed. No other project's process or data was touched.

The145-member proposed overlay retains the real loader descriptor's144 source
and11 support literals. `source-manifest.json` makes that mismatch explicit;
metadata compilation establishes no genuine loader/profile descriptor binding.
Native/device checks remain paused and pending. Independent delta review,
owner-base correction/acceptance, actual delegation/admission integration,
complete work/lifetimes, descriptor requalification and all canonical, OTA,
FieldLog, store/customer and GA gates remain pending.

Read-only packet checks:

```
PYTHONDONTWRITEBYTECODE=1 python3 verification/swift-guarded-snapshot-emission-storage-delta/check.py --verify
PYTHONDONTWRITEBYTECODE=1 python3 verification/swift-guarded-snapshot-emission-storage-delta/freeze.py --verify
```
