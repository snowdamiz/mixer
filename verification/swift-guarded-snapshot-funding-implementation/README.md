# Isolated exact snapshot funding implementation

This source144 candidate replaces the placeholder snapshot storage grants with
the root-accepted logical recipe **C78,240 / S941,467 / A430,175 / H81,327**.
It changes only `control.rs` and `cache/initial_profile_v1.rs` from the frozen
authority225/source144 tree
`575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896`.
The candidate source tree is
`7e3e861ca65d8c6359623443d6a7810b878c1029494a0ae557307d35ed43484b`.
`source-delta.patch` records every change. Canonical product files are untouched.

The unchanged Original const initializer remains the sole **F0**. The common
adoption function copies const **Fcommon=F0+C**. The selected function copies
const **Fselected=Fcommon+S**; cfg(test) conservatively adds H at the actual
selected Construction admission. Production excludes H. The selected conditional
phase preflights and would commit exactly A on its existing construction ticket.
The totals over F0 are 1,019,707 selected bytes, 1,449,882 admitted bytes, and
1,531,209 admitted bytes including the concrete cfg(test) caller. Placeholder type
aggregates remain available to historical layout probes but no longer grant
bytes, and they are not added again. Neither the 2,192 optional credit nor any
removed-role credit is selected.

Both candidate production and cfg(test) metadata/MIR compilations pass on
**rustc 1.99.0 / aarch64-apple-darwin**. Fresh unoptimized compiler MIR confirms
that both changed floor functions have only their existing `Option<usize>`
return place. All new arithmetic and cfg selection is const-evaluated. There
are no added runtime helpers, calls, locals or type/field layouts. The old
selected-floor function's 200-byte conservative source-role charge is retained
in full. `source-delta-accounting.json` binds the exact compiler evidence.

Three standalone Rust scalar executions each pass 174 synthetic integer phase,
overflow and refusal controls. They exercise the exact extracted constant block
in production, cfg(test), and overflowing-F0 contexts, without linking Mixer.
The 32-bit and 64-bit arithmetic cases are mathematical models, not target
qualification. The synthetic F0 of 366,896 in the positive scalar harness is
explicitly not a newly measured Mixer floor. A fourth scalar compiler command
produces the expected checked-overflow E0080. Thirty-four exact source,
ordering, preservation and fresh-MIR accounting controls pass separately.

The existing **WorkAuditPending** refusal remains before A commit and before any
transfer buffer or writer admission. No emission helper or delegation is added,
and its separately accepted 17,728-byte hypothetical delta is not charged here.
The fixed 256 MiB memory and 1 billion work policies and original 300,000/400,000
fixture grants remain unchanged. Larger common funding may make the unchanged
400,000 fixture refuse earlier than its historical downstream boundary; this
packet does not dispatch those fixtures or raise their limits.

Two integration obligations remain explicit in `lifetime-obligations.json`:

- The cfg(test) H charge at selected Construction admission does not prove
  ownership/reservation of already-live pre-ingress host arguments, independent
  external harness IO/assertion costs, or the separately retained unit
  instrumentation. Seven concrete host argument roles are named. The future
  genuine caller is compiled but undispatched and unqualified.
- `SnapshotAccessV1::complete` retains its original pairing/error semantics and
  currently narrows admitted A to the previous selected total. The report names
  13 A producer return roles, five writer return/move roles, and 24 already-funded
  S receiving roles in the escaping diagnostic chain. The S receiving slots are
  already charged; review must still establish that every A producer/owned backing
  lifetime ended or transferred before that refund. `lifetime-retention-follow-up.json`
  describes the unselected next option of returning the already computed committed
  construction total as the completion retention target, preserving the normalizer's
  validation/error branches. This packet does not apply that amendment.

All diagnostic outcomes, original eight primary variants, selected capability
ownership, completion bodies and final conservative **ConstructionBound**
retirement remain unchanged. The selected charge stays enlarged at the final
cleanup boundary; healthy cleanup remains unqualified. No engine, VM or writer
fixture executes. Compiler artifacts and standalone scalar binaries are removed,
and only recorded owned process groups are rechecked. No native/device/simulator/
emulator/UI/capture operation or global process inventory occurs. Those checks
remain paused/pending. Linux CI for a separate canonical diagnostic slice is not
evidence for this isolated candidate. Writer release, full operational funding,
production caller qualification, OTA, FieldLog and all GA gates remain pending.

The accepted recipe input is copied with its exact root receipt digest in
`accepted-recipe-input.json`; its acceptance is logical source scope only.
Rebuild drivers write evidence and must be run only in a new unfrozen copy after
this packet is sealed.
