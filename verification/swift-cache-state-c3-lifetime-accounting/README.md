# Correction-3 source lifetime proposal

This packet proposes a complete finite source-role accounting for frozen
`cache_state.rs` SHA-256
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8`.
It inherits only the exact selected safe-File framing/envelope closure and its
24,656-byte inventory, with byte-exact prefix bindings. It adds explicit source,
constructor, received, call, return, branch and immediate caller phases for the
new path. It is a producer proposal requiring later independent review. Passing
the offline verifier grants no gate, work-bound, implementation, OTA or GA
acceptance.

Run from the repository root:

```
python3 -B verification/swift-cache-state-c3-lifetime-accounting/verify.py
python3 -O -B verification/swift-cache-state-c3-lifetime-accounting/verify.py
```

`run.py` regenerates the owned unsealed proposal from `build.py` and preserves
separate exact commands, tool identity, raw stdout/stderr and return codes in
new `commands/<timestamp>/` directories. It executes only this packet's own
standard-library Python. It does not import an old collector, ledger, test,
harness or product source. The final manifest binds every owned packet member;
`seal.py --verify` checks it without regeneration.

The fixed role union stays 29,344. Reservation stays 41,984, global ceiling stays
65,536 and the 23,552 unassigned margin remains unused. Candidate remains one
retained 2,048-byte destination; its complete initializer source already belongs
to inherited Setup. The proposed added phase maxima are Control 1,201 of 1,280,
Wire 152 of 256, Setup 160 of 256 and Report 2,688 of 2,896. IO, Metadata and
Candidate add zero. These are conservative authored-source roles, not measured
stack, RSS, compiler ABI, allocator, kernel or libstd internals.

The role and phase mapping is split into:

- `inheritance.json`: exact selected acceptance/inventory/source prefix bindings
  and old-to-new function crosswalk. Existing source, received, metadata,
  Stamp, profile72, complete private Result40/64/80 and envelope values remain
  charged. The whole old role bound is conservatively retained on every phase.
- `named-places.json`: 191 actual named Rust variables/parameters, lexical scope
  ends, byte sizes, roles and inherited/new identity. Last use never retires a
  named local. Shadowed publication slots coexist.
- `templates.json`: explicit helper endpoint objects. The read/forward union is
  456 bytes and the write/sq/st union is 424. Those derive from named objects;
  the rejected historical helper192, Option112 and leaf256 claims supply no
  credit. Full Option16 constructor/return/received objects include final None.
  Option borrows use their complete eight-byte niche representation. Slice
  views retain data and length; Ranges retain both fields. Scalar primitive
  boundaries follow the selected G6 authored-source model.
- `source-sites.json`: exact frozen loop/copy/checked-Option coordinates. The
  mapping covers finite loop templates, each individual clear statement and all
  twelve restores. Syntax coordinates alone supply no acceptance authority.
- `phases.json`: explicit added live-place rows and per-role peaks, composed
  with the inherited closure. Some mutually sequential subphases are unioned
  deliberately. A shared view or contained field never creates a second byte
  payload; source and received value objects remain separate.
- `return-moves.json`: all early error families, successful aggregate, complete
  public Result and immediate external receive/extraction. Five inherited
  232-byte aggregate/Result slots expand to 488 (+1,280). Five new 256-byte
  observation slots (+1,280) cover initializer, constructor, local, designated
  return and outer receive. Four extra Error32 slots add128. The conservative
  sum 2,688 fits Report2,896. Existing field sources and fields inside whole
  aggregates are identified as aliases and never allocated twice.

The outer `cache_walk.arena: &mut Arena` is a separate eight-byte object from
the existing Vec24 and each slice16. It is explicitly added. Each clear has one
anonymous array128, Paid24 and complete additional metadata/handles in Control.
The 152 subtotal is only its Wire payload subtotal. The array's slice receiver
references the same128 bytes; it does not create another128-byte array. One
statement ends before the next. Semantic callee locals end before cleanup;
Loan16, semantic StepBudget16, received SemanticReply24 and old envelope reply
remain live in their actual caller scopes.

The accounting boundary is one safe-File library invocation and the immediate
external caller complete Result receive plus one extraction/branch, matching
the predecessor scope. It does not bound arbitrarily deep application
forwarding stacks. Full source/received Result488 is charged on Err paths even
when only its Error32 payload is active. No optimizer return-value elimination,
array promotion or inactive enum-byte discount supplies the bound.

The first two recorded checks passed; no failed execution attempt occurred in
this lane. Unsealed authoring refinements added closure/Option receiver objects,
complete helper forwarded return objects, Candidate coercion endpoints and exact
while-versus-for distinction before the final seal. Earlier recorded successful
outputs remain intact. The final run is named by `latest-run.json`. Nine mutation
controls reject input drift, role overflow, duplicate live endpoints, missing
clear payload, incomplete Option, narrowed receiver, Result232 regression,
margin use and an acceptance overclaim under normal Python and Python `-O`.

No product or old packet was written. No Rust compiler/product runtime,
simulator/emulator/device, UI automation, capture, process discovery, Git action,
hosted read or forbidden hosted lane was used. The host layout and Result488
fact is inherited from the exact accepted correction3 host receipt. Newly unrun
native/device checks remain pending. Complete independent lifetime review,
G3/G4 and combined source work acceptance, independent implementation replay,
real binding/custody, immutable published FieldLog, signing/store/customer/
operations and accountable GA review remain pending.
