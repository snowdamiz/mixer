# Independent private Swift memory contract review

I recommend root accept the frozen Load/Store **contract, borrow/type and logical
accounting prerequisite**. I found no unresolved blocker within that boundary.
This is a review recommendation, not root acceptance, permission to integrate the
overlay, behavior acceptance, or qualification of any release gate. The binding
product scope remains `mixer-product-plan.md`.

The reviewed producer receipt SHA-256 is
`57685ea8486d7387ef708d00427bb21e0fdb61c4f97559b31ec6f03b038b20fa`.
All 319 retained bindings and all 34 qualifying command receipts/raw output hashes
were checked independently. The accepted private control authority supplies the
121-file baseline closure
`241f7a6037100d29a4d277e1ec176fec55c0380b4283c17120bb8ace045318d5`.
The isolated candidate is the exact 122-file closure
`b0922009f9fbb9b2b1091ec4b62607cff456288e8d044217481c31bfe826596c`.
Only the five declared files differ. Live VM source was not changed.

## Independently reproduced evidence

The review uses its own collector, source/MIR parser and metadata instrumentation;
it imports no producer parser, inventory generator or layout checker. Both exact
source archives and both independently instrumented source archives are retained
under `verification/swift-memory-helper-contract-review/`, together with raw
compressed output, argv, selected environment, before/after source digests,
compiler MIR and hashes of the sixteen metadata executables. Rust and Cargo are
1.99.0 on aarch64-apple-darwin.

Fresh compilation checks the actual private phase, fixed storage slot and pinned
caller, using the original cache/control/WASI borrows. Eight library checks pass:
default, span, Swift-only and all features, each in Debug and Release. Eight
candidate metadata configurations, each paired with a freshly compiled baseline,
cover Swift-only/all features, Debug/Release and production/unit. Each selected
unit run executes exactly one metadata-only test. Those executables print
size/alignment/offset constants and compile method pointer assignments; they
invoke no memory helper, caller witness or guest opcode.

Fresh expanded source independently reproduces all 39 complete Frozen
`SpanInstance` methods byte-for-byte. This includes range/load/store/run/copy/fill/
grow. The original width body is unchanged apart from visibility, and the same
literal shared macro supplies both memory paths. The original Frozen reservation
expression and measured 2,912-byte result are unchanged. Every existing struct
and enum declaration in the four modified old files is preserved, all remaining
old files retain their hashes, and fourteen specifically selected original owner
declarations are identical. Original measured types and owner offsets also match.

The fresh production and unit canonical MIR each contain eighteen selected
functions/closures and two promoted constant bodies. The independent inventory
finds 529 entities per configuration: actual arguments, return places and locals,
explicit source aliases and typed direct literals. Every entity maps to four
separate source/argument/returned/caller fields. Six anonymous capture payloads
are derived from actual MIR field projections, including the memory Vec borrow,
mutable original phase borrows and empty capture. Both promoted returns and their
Type/RangeInclusive backing places are counted separately from the references
that use them. Compiler debug projections name the captured backing and do not
create a second runtime owner. Zero-sized unit debug constants and type-level
array-length constants do not represent extra runtime storage.

All 4,688 actual field declarations match the schema: 2,116 production MIR fields,
2,116 additional unit MIR fields, 404 authored active fields and 52 authored
permanent fields. Each observed field is aligned, disjoint and contained within
its full measured accounting struct. No old field, equal-layout alias, old padding
or Frozen scratch supplies credit. The complete original value and control
envelopes remain included once. These are logical requested/named-object bounds;
they establish no compiler-stack, allocator-overhead, optimizer-temporary or RSS
bound.

| aarch64 host observation | Production | Unit |
| --- | ---: | ---: |
| Fresh memory permanent addition | 121,856 | 121,856 |
| Fresh memory active addition | 618,896 | 1,153,832 |
| Execution header after addition | 1,636,360 | 2,531,040 |
| Frame envelope after addition | 2,830,864 | 5,103,960 |
| Unchanged construction envelope | 1,069,144 | 1,071,904 |
| Unchanged nested value envelope | 119,576 | 119,576 |

The header adds memory permanent bytes to the original header formula. The
frame formula adds memory active bytes once after the original frame, value and
control terms. Existing preparation admits that full bound before creating the
phase and retains the original previous/admitted record. State/Combined limits
remain 128MiB/256MiB; the unchanged ticket authority caps tickets at 86.

## Source and ownership assessment

The entry checks slot vacancy before active-owner checks, operation inspection,
work, operand removal or memory effects. Occupied success and failure outcomes
are preserved; the original RuntimeControl `fail` implementation preserves any
first failure and terminal marks request existing drain. A vacant slot receives
one inner result, including failure. Outer `Ok(())` means publication only. The
future caller must inspect the stored outcome before fetching again, take/drop a
successful outcome before reusing the slot, and retain failures through drain
and the original consuming completion API.

The actual existing `FrameOperationStorage.entry` carries that outcome in the
compiled caller. Original entry guards and pins stay in State. No storage field,
instantiated owner, cleanup authority, ticket, ledger, proof copy or dependency
is introduced. The original fixed completion consumes real storage, drops the
parts/storage tuple before restoration, or preserves bound/debt on failure. Its
implementation and conservative incomplete-phase handling remain unchanged.

Source review confirms preflight checks only the admitted load/store scalar
ranges, a real current frame, `base <= operands <= values.len()`, the frame's
control-vector floor, sufficient operands above the frame operand floor, I32
addresses and exact store value types. A malformed floor, missing value or wrong
type cannot consume caller/local operands. `active()` still checks original
owner/live agreement. Unsupported operations fail closed before inappropriate
operand mutation.

The shared load/store bodies preserve address zero extension, checked offset and
range arithmetic, width work before byte access, little-endian padding/conversion,
signed and unsigned extension, floating bit payloads, and bounded store publication.
The original pop charges work before the actual pop, then removes live count;
the original push charges work, checks agreement/floors/capacity and debits live
count immediately before publication. The wrapper marks original cleanup debt
when the accepted pop fails after an actual length reduction, returning the
original error unchanged. No new fallible debit/check follows that effect.

The uncalled caller selects the actual decoded instruction through the retained
frame pin, copies its function and instruction, ends the cache view, sets the
actual cursor, charges instruction/fuel and outer work once, then checked-advances
PC once before helper dispatch. It introduces no cloned pin or second cache.
The helper itself adds no instruction/fuel debit, PC mutation, allocation or
memory growth.

## Required subsequent work and exclusions

The caller is only a compiler witness. In particular its early active/view/fetch
errors return directly; it is not complete production terminal-drain/error-path
orchestration. The behavior lane must deliberately implement and execute those
paths, inspect stored outcomes, prove occupied-slot preservation and invoke the
actual original drain/completion route. This known limitation is explicit in the
producer contract and does not block this type prerequisite.

All sixteen MM01–MM16 acceptance groups remain pending. No opcode semantics,
work/cancellation prefix, allocation refusal, runtime Frozen parity, cleanup
restoration or final host execution claim follows from the compilation/layout
results. The next lane must execute all exact groups in all four host
feature/profile configurations under the frozen fixture bounds, then obtain
independent and root review. Root must accept this prerequisite before that lane
starts; this review does not apply the source overlay.

The accepted post-pop `Cleanup` diagnostic can still omit function/offset/resource
and retain actual WASI observation. No source cursor is manufactured here; G08
remains open. Other target widths and native targets remain unverified. Copy,
fill, MemorySize, growth and its separately borrowed original `buffers[3]` ticket,
full dispatcher/calls/host imports, Ready/public invocation, bounded full-target
runner, native joins, immutable separately published FieldLog packages, final
physical-phone matrix, signing/store/customer/operational and GA gates remain
pending. No UI/device, customer message, credential change, commit, push or
production publication was performed.

Two failed review-checker attempts are preserved and excluded: the first grouped
repeated alias names instead of individual bindings; the second required a fixed
indentation and therefore selected zero Frozen methods. Corrected independent
parsing, fresh compiler results and final offline verification provide the
qualifying evidence. No product source correction was needed. Owned source/build
scratch was archived, verified and removed; no simulator/emulator or phone was
started, no process was terminated, and other projects' data was preserved.

Run the retained offline verification with:

```text
python3 -B verification/swift-memory-helper-contract-review/verify.py
```
