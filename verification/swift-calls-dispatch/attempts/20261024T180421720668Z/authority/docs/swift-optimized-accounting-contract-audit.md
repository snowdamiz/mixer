# Optimized accounting: independent contract audit

Status: **audit complete; accounting and runtime acceptance remain pending**.
This packet offers a reviewable proof choice. It does not amend the selected
contract or approve pointer erasure, equal-size aliases, tuple closure aliases,
byte-array placeholders, omitted bodies, owner changes, or relaxed budgets.

## Decision

Retain exact typed witnesses wherever stable Rust can express the actual type.
For this frozen inventory, the 432 `!` positions have a demonstrated stable exact
typed route; the eight `Arc<Atomic<bool>>` positions have the root-approved true
`AtomicBool` alias. The 16 private Mixer `Kind` positions can remain exactly typed
in a child of its defining module without widening visibility. That last route
was proposed by the producer and source/privacy reviewed here; it was not
implemented or separately compiled against Mixer by this audit.

**248 positions still lack a demonstrated stable expression exposing their exact
std identity.** They include owned private values, not only private pointees.
Compiler layout records can establish their size/alignment, but substituting a
same-sized accessible type would violate the existing contract. If root chooses
compiler layout authority for these roles, it must explicitly approve that
separate proof method under the fail-closed obligations below. It is not an
already-satisfied typed-field proof.

A second issue is independent of those 248 positions: the current generator
replaces 560 closure-typed positions (13 distinct raw type expressions) with tuple
capture types. A tuple is not the actual closure type. This audit's negative
compiler test rejects that equality. No such substitution receives credit here.

## Exact evidence and inventory

`verification/swift-optimized-accounting-contract-audit/input-bindings.json`
binds the selected contract, root selection/amendments, producer generator and
inventory snapshots, and the retained declaration failure. The declaration
failure is producer attempt `20261024T153842803467Z`, exit 101, source closure
`3a56910ee8503fc26776b69e1bf758e6333df78384945ad6e0b7e378704469e0`.
Its complete compressed stderr, command and source manifest are retained in the
audit input snapshot. The producer's original failed declaration remains intact.

`exact-private-inventory.json` lists every affected named reservation position,
configuration, full body/header, actual MIR binding and source alias. For each
unique source position it additionally records the exact body's digest and
all declaration/use lines for that local. `raw-mir-bindings.json` binds all eight
original raw MIR dumps, their source closure and compiler attempts. Four roles
(source, argument, returned, caller) are positive reservation positions; they are
not a claim that the compiler observed four distinct runtime values.

The 82,732-row input contains 704 positions in the producer's 16 unnameable groups.
The following observed sizes apply to this aarch64 host/compiler context; they
are not cross-target guarantees. Private value layouts are producer-observed
compiler metadata, retained in `inputs/unnameable-layout-evidence.json`, from its
Release production/unit compiler staging attempts, which had pending accounting.
The size of a reference/pointer is the transfer size, not the pointee size.

| Group | Actual type / role | Positions | Bytes / alignment | Exact stable typed route |
| --- | --- | ---: | ---: | --- |
| U01 | `&EagerStorage<Cell<bool>>` | 16 | 8 / 8 | Residual |
| U02 | Owned static initializer `EagerStorage<Cell<bool>>` | 16 | 2 / 1 | Residual |
| U03 | `&EagerStorage<Cell<usize>>` | 16 | 8 / 8 | Residual |
| U04 | Owned static initializer `EagerStorage<Cell<usize>>` | 16 | 16 / 8 | Residual |
| U05 | `&EagerStorage<Cell<Option<usize>>>` | 16 | 8 / 8 | Residual |
| U06 | Owned static initializer `EagerStorage<Cell<Option<usize>>>` | 16 | 24 / 8 | Residual |
| U07 | `!`, uninhabited return/local | 432 | 0 / 1 | Demonstrated inferred `Roles<!>` |
| U08 | Owned `UsizeNoHighBit` | 48 | 8 / 8 | Residual |
| U09 | Owned Mixer `Kind` | 16 | 1 / 1 | Defining-module child; source reviewed |
| U10 | Owned TLS eager `State` | 24 | 1 / 1 | Residual |
| U11 | `*mut TLS State` | 24 | 8 / 8 | Residual |
| U12 | `*const UnsafeCell<TLS State>` | 24 | 8 / 8 | Residual |
| U13 | Owned `Arc<Atomic<bool>>` | 8 | 8 / 8 | True `AtomicBool` alias |
| U14 | `NonNull<ArcInner<Atomic<bool>>>` | 16 | 8 / 8 | Residual |
| U15 | `*const ArcInner<Atomic<bool>>` | 8 | 8 / 8 | Residual |
| U16 | `*const UnsafeCell<Align8<usize>>` | 8 | 8 / 8 | Residual |

U01–U06 belong to the exact `PC_OVERFLOW`, `CHECK_COUNT` and `CANCEL_AT` generated
TLS bodies. U08 appears in changed production bodies after std inlining. U10–U12
are in the generated TLS getter closures. U13–U16 are in the unit runtime
`checkpoint` hook. These runtime hooks cannot be relabeled fixture builders: the
selected owner-preflight amendment requires reachable unit hooks/TLS to receive
positive accounting. Their exact callers and bodies are retained per position.
`!` has no inhabiting runtime value; its zero-size roles must remain explicitly
listed and exactly typed, rather than being silently removed or called owning
allocations.

## Successful stable experiments

All twelve small experiments use rustc 1.99.0
(`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, LLVM 23.1.1), host
`aarch64-apple-darwin`, edition 2024, opt-level 3. `RUSTC_BOOTSTRAP` is removed.
Commands, source hashes, raw MIR, outputs, positive and negative results are
retained below `verification/swift-optimized-accounting-contract-audit/experiments`.
No Mixer build or runtime test was run by this audit.

The working typed construction is:

```rust
struct Roles<T> { source: T, argument: T, returned: T, caller: T }
const fn returned_roles<T>(_: fn() -> T) -> usize {
    std::mem::size_of::<Roles<T>>()
}
fn never() -> ! { panic!("not called") }
const NEVER_BYTES: usize = returned_roles(never);
```

Rust infers the actual never type. The experiment's raw MIR contains
`roles_of_return::<!>` and returns 0 bytes, alignment 1. The factory function is
never executed, and no `Infallible` value or substitute type appears.

Function items also remain exact types: `roles_of_value(never)` instantiates
`Roles<fn() -> ! {never}>`, size 0 / alignment 1. It is not charged as a function
pointer. Function item types have distinct identities even when their signatures
are equal. [Rust Reference](https://doc.rust-lang.org/reference/types/function-item.html)

An accessible closure factory can supply its exact opaque return type to a
generic witness. The successful borrowed-factory experiment uses:

```rust
fn factory(v: &mut usize) -> impl FnMut() -> usize + '_ {
    move || { *v += 1; *v }
}
const fn returned_roles<T>(_: fn(&'static mut usize) -> T) -> usize {
    std::mem::size_of::<Roles<T>>()
}
const BYTES: usize = returned_roles(factory);
```

Its MIR explicitly instantiates the actual closure type. Four typed fields occupy
32 / 8. No mutable reference or owner is constructed and the closure constructor
is never called. This is a feasibility proof for an accessible factory, not proof
for an existing inaccessible lexical closure. Moving a production closure into a
factory would change source/body identities, require all accounting regeneration,
and must preserve all Frozen expansions; it is not authorized by this audit.

The original attempt to measure an opaque factory result directly in a constant
failed because its unconstrained destructor could not run in const evaluation.
That failure is retained. A `Copy` bound works for the owned simple factory;
inferring the return type from a function item also handles a mutable-borrow
closure without constructing it.

Negative tests retain: naming `!` as a stable struct field, directly naming hidden
std types, reading `Arc`'s private pointer field, using `_` as a struct field type,
and identifying a closure with its capture tuple. A separate stable
`thread_local!` microprogram reproduces the inaccessible `EagerStorage`/TLS State
locals in optimized MIR while the public getter exposes only its payload.
`size_of_val` requires a reference to a value of the actual type; it does not
recover a hidden internal local through an enclosing public object.
[Rust API](https://doc.rust-lang.org/std/mem/fn.size_of_val.html)

## Narrow proposed alternative requiring root decision

The minimum residual alternative is **compiler-derived exact-identity layout
authority**, initially restricted to the 248 private std positions above and
any specific closure identity for which no exact inferred witness is supplied.
It must be labeled as compiler layout evidence, not typed source-field evidence.
Do not grant a generic pointer-sized transfer exemption. Require all of:

1. Freeze exact baseline/candidate source archives and compiler/sysroot identities,
   target triple/data layout, feature set, profile, production/unit cfg and command
   flags for every required context. Compiler staging must prove runtime bodies
   match the final candidate, not merely claim their equivalence.
2. Select complete full body identities, including every free body, closure,
   promoted/static initializer and reachable unit hook. Retain the fixture-only
   boundary from compiler evidence. Inventory typed locals, arguments/returns,
   authored aliases, literals, captures and transfer roles without filtering away
   unnameable types. Audit implicit function-item operands separately; this audit
   does not certify that the current declaration parser inventories every one.
3. For every exceptional position, bind exact raw MIR type identity and local,
   full body digest, owning/borrowed/nonowning status, caller, layout evidence and
   distinct permanent/frame class. No inference from matching spelling alone,
   no tuple/byte-array/type substitution presented as identity proof.
4. Require a compiler-produced layout for the **actual concrete type**, including
   size/alignment, fields/offsets and variants where relevant. A pointee's layout
   is not the pointer's layout. A pointer-size language guarantee may corroborate
   a transfer calculation but cannot fabricate the missing typed identity.
5. Use checked, additive per-position arithmetic with alignment and disjoint
   intervals, including zero-sized named roles. A recorded compiler size may feed
   a deliberately declared numeric bound only under this new authority; a stored
   byte placeholder is not a typed witness. Do not subtract old positions,
   overlap old padding, reuse earlier rows or count optimizer elimination.
6. Reject missing/duplicate bodies, changed identities/layouts, unknown types,
   unbound closures, missing target/config records, source drift, unsupported
   compiler output, arithmetic overflow and incomplete field/layout metadata.
   The exceptional manifest must be finite and explicit; a new private type fails.
7. Re-run all eight candidate MIR contexts and all sixteen baseline/candidate
   layouts with the final actual reservation formulas. Verify original owner
   declarations/fields, all 39 Frozen expanded methods, Frozen 2,912-byte bound,
   prior positive positions, State/Combined limits and ticket maximum 86. If the
   complete positive bound exceeds a limit, preserve rejection and return to root.
8. Keep runtime qualification blocked until independent review accepts this method,
   its exact packet and the actual complete bound. No private pointer rule alone
   discharges the 120 owned-private-value positions, and no metadata-only run is
   runtime acceptance. No Ready/public lifecycle, allocation, native, device,
   signing, store, FieldLog, G08 or GA credit follows.

Root's alternatives are therefore concrete: retain the exact-type obligation and
supply accessible inferred witnesses/refactor only permitted source, leaving the
residual private roles pending; or explicitly approve the finite compiler-layout
proof method above and qualify its implementation separately. Equal-size aliases
are unnecessary for `!` and unsupported for every residual identity here.
