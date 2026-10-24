# Private Swift bulk-memory implementation evidence

The isolated candidate implements the shared original Frozen copy, fill and
MemorySize semantics through the actual Swift frame phase, fixed result slot,
original control/WASI/cache/state owners and retained frame pins. Its 125-file
source closure is
`e5050427a9653019e429bd6cb050133e89617d9a40c9896e0d684f12aa7c8626`.
The exact private contract is [swift-bulk-memory-contract.md](swift-bulk-memory-contract.md).
Independent review, root integration and product acceptance remain separate.

## Executed behavior

BM01–BM16 execute exactly once per Swift-only/all-feature Debug/Release
configuration, together with the 62 prior frame/control/value/memory selections.
The final matrix contains 78 successful tests per configuration, 312 total,
including 64 fresh bulk selections. Every bulk group reports finite bounds:
at most 64 fixture owners, 64 counted helper/caller attempts per fixture, three
frames and actual 584-page ABI memory. Execution is serial within each command.
These are host receipts, not iOS/Android or physical-device evidence.

| Groups | Actual observations |
| --- | --- |
| BM01–BM03 | Copy overlap in both directions, equal addresses, disjoint ranges, multiple chunks, fill low-byte behavior, zero length, end-of-memory, high-bit and out-of-bounds ranges. |
| BM04–BM06 | Original frame/floor/type/page checks before pops; pop/work effect prefixes; fuel rounding and denial at 0/1/63/64/65/129 bytes. |
| BM07–BM08 | Cancellation before each pop/work boundary, zero-length cancellation, and exact forward/backward/fill completed chunk effects after full bulk debit. |
| BM09–BM11 | Observed MemorySize value and real push-capacity failures; actual pinned decoded Copy/Fill/MemorySize callers; exact cursor/PC/fuel/work/pin observations; early active/fetch/cache/work/cancel/PC and instruction/bulk fuel errors. |
| BM12–BM13 | Occupied success/failure preservation, stored-outcome interpretation, actual fixed completion, post-pop live debt, three retained original pins and explicit cleanup retry. |
| BM14–BM16 | Zero observed warm allocation requests on success and failure, deferred-opcode rejection, actual/live corruption, successful slot reuse and exact additive reservation restoration or conservative retained debt. |

The whole accepted memory accounting suffix remains byte-identical. MM16 and
AF22/SC11 retain their old memory component while including the fresh additive
bulk component in complete-envelope expectations. Existing interpreter semantics
and test assertions otherwise retain their accepted bodies.

## Identity, accounting and prerequisites

Final compiler expansion reproduces all 39 Frozen method identities and all
fourteen original containing-owner declarations. Thirty-two finite actual Frozen
fixtures per Debug/Release profile give 64 identical baseline/candidate
observation pairs: results, full-memory digest, bytes, traps, fuel/work/cache
usage and synchronous allocation requests. These include large overlapping copy,
low-byte fill, zero/boundary failures, MemorySize and the unchanged excluded-growth
regression. Four fresh 16-test Frozen integration runs also pass.

The 4,324 new positive positions and all 4,800 retained memory positions are
replayed from four final compiler MIR configurations, including compiler-promoted
return/backing places. Three collector selection regressions pass. Sixteen paired
actual metadata runs measure all fresh intervals, containing bounds and original
owner layouts. These observations establish the named-object accounting and
borrow/layout prerequisites separately from the executed behavior above.

Eight final default/span/Swift/all Debug/Release library checks and the current
Swift-only CI Clippy command pass. Rust/Cargo are 1.99.0 on aarch64 Apple Darwin.
Every executed command records argv, cwd, selected environment, exact source
manifest/closure, output/status, and executable hash where applicable. Source
archives are retained for final, instrumented and historical failed attempts.

Historical draft failures are retained and excluded: a private test-hook
visibility error, invalid fixture restoration through an already sticky failure,
a missing foreign-header fixture for an injected release failure, two temporary
visibility-macro parsing attempts in the Frozen configuration, the initial
complete-envelope regression expectation, and Clippy's page-alignment style
finding. The final implementation resolves each. The first canonical comparison
also rejected compiler function-name qualification after the coordinated
visibility change; its exact script and qualification-only delta are preserved.
The corrected comparison requires exact field/type/binding/position equality and
normalizes only that explicit containing-module prefix. No skipped or failed
attempt is reported as a final pass.

The read-only checker is:

```text
python3 -B verification/swift-bulk-memory/verify.py
```

It reads sealed source archives, hashes, raw command evidence, canonical MIR,
measured intervals and executed-test identities without compiling or mutating
source. `--live-baseline` additionally requires the current VM to reproduce the
accepted normalized input closure. The source patch is review material for root;
this lane performs no live VM edit, tracker edit, commit, push, publication or
customer message. Scratch cleanup is recorded in the packet and preserves other
projects' processes, instances and data.

Growth, host calls, full dispatch/Ready/public invocation, native joins, the full
Swift target, immutable published separate-repository FieldLog, final phones,
signing/store/customer/operational and GA gates remain open. G08 remains open.
