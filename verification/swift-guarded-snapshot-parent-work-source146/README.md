# Source146 P0 account-surface rebind candidate

Prepared for independent cross-review; **not yet accepted** as source146 work
pricing. Pure source/MIR/compiler-data reconciliation passes 3,051 checks and
recalculates the candidate expression:

`W_P0_account_surface = 2628088 + 194231*I + 1039*U`

The fixed dimensions remain 416,998 abstract source actions plus a 2,211,090
native-sized occurrence allowance, including the ten-row 131,334-unit finite
primitive drop addendum. This allowance describes logical work; it is not
actual physical byte copying, storage, CPU time, stack, RSS, or allocator work.
Neither `I` nor `U` is selected or defaults to zero.

## Binding and source changes

The prior source145 review is immutable: seal SHA-256
`ffdd027f5550f315fb7c63dcee7e532e7aea1d4be39c478d225f8f6ed09a7b2b`
(46 members, 767,864 bytes). Root's parent-work acceptance is
`guarded-snapshot-parent-work-host-acceptance.json`, SHA-256
`479d0fd1114cd7512c369dae0038a7ccd2407854f5089669ba5e020f2225cd3a`.

The exact accepted composition distribution has 146 members and tree
`690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`.
Root's composition acceptance is
`guarded-snapshot-host-composition-host-acceptance.json`, SHA-256
`c176aa3802d267d1e5bac6c5c281b1122058d81c4fbc5fa3eff49a05ca404ee8`.
Both frozen composition closures were rehashed: producer seal
`2fc002b2598effdc70a74ecfa3da775b4aa82f2572cbbb93650207925238dc2e`
(152 members, 1,301,753 bytes), independent seal
`c9ccf4649a4dd5c11ac62d403e6443f58dd018562d667f76d16dc422354f3e63`
(96 members, 1,453,031 bytes).

Relative to the accepted account145 tree, source146 retains 142 members
unchanged, changes the profile, control, and loader files, and adds the private
853-byte emission helper. The net source addition is 2,786 bytes. The account,
bootstrap, and typed entry bytes remain exact. The helper stays undispatched.
`source-delta.patch` preserves the complete difference without creating a
checkout. The `SnapshotAccessV1` field-name-only `previous` to `retained` change
is outside this component's shape closure; **all 54 priced declarations are
byte-identical**. Changed control/emission/loader work remains outside this
P0 component and is not silently imported into its price.

## Compiler-data and work reconciliation

No compiler was invoked. The existing accepted source146 independent packet
provides raw retained 19-function MIR, 396 raw roles, 90 fresh concrete layout
diagnostics, the exact selected closure size, and complete compiler-output
archives. Both build identities were rebound from their five length-prefixed
manifest/argv/environment/compiler/version preimages. The metadata distribution
is exactly source146. The separate query distribution is reconstructed as that
source plus only its named diagnostic module and never-type feature directive;
it creates no root or fixture constructor. Rustc1.99.0 aarch64-apple-darwin is
read from frozen receipts, not launched here.

Every complete retained MIR body and raw role type matches source145 after
normalizing only the exact frozen compiler scratch root, compiler source spans,
and comments. All 15 P0 functions/208 roles are then remeasured from the fresh
diagnostics, including four exact 8-byte selected-closure role instances. The
54 source-visible shape definitions, every one of 613 operations, every written
normal/refusal/cleanup/unwind alternative, every entry and implicit return,
and all full pointee surcharges are recalculated. The result retains 234,375
logical inventory bytes, a 2,556-leaf/13,608-byte payload, a
2,560-leaf/13,624-byte wrapper, and 273 bounded terminal paths.

The ten finite drop rows are recomputed at fresh measured extents. The account
source is byte-identical, preserving one authored P0 wrapper Drop body across
explicit/ordinary/cleanup alternatives and `owned.take()` before payload
destruction. At most one actual payload destruction remains a separately
**required nonzero P5 cost**. No standard-library/compiler/kernel/allocator
private implementation or retries are claimed to be priced by the inherited
closed source-level primitive unit.

Focused controls reject semantic literal/control mutations, an unknown compiler
scratch identity, a different source tree, a changed fixed-array field shape,
an 8-byte substitute for the real aggregate, and a new authored callback. These
checks do not authorize future changed constructors. Two failed preparation
assumptions are preserved under `attempts/`: compiler display elision for a long
type, and the location of a field-name-only declaration change. Exact successful
preparation and read-only reproduction commands, Python3.14.8, helper/driver
hashes, source digest and outputs are in `command/` and `check-command/`.

The bounded helpers are copied from the accepted source145 independent checker;
`helper-provenance.json` names that exact origin. Its audit/producer code is not
executed or imported. This preparer is not a substitute for another author's
source146 cross-review.

## Required cuts and acceptance boundary

The exact selected root/quote/constructor/caller route, finite `I/U`, immutable
fixture binding/backing, eventual P0 dynamic/native backing, and complete P0
work/storage remain unknown. P0 must be provisioned before quote/account/child
admission and retained through token release; child refunds cannot fund it
retroactively. Both selected constructors still return Pending. All six child
parts remain required, including original loader validation and separate P5
returned-carrier plus actual payload-destruction terms. Generic shared `&T`
does not prohibit cloning/interior mutation; future inspecting callers need
their own source/ownership/work/backing review. Missing or changed evidence
cannot inherit this candidate pricing.

There is no selected policy/grant, complete P0/host quote, fixture/executable
qualification, physical/performance bound, native/OTA/FieldLog/customer/GA
acceptance. Native checks remain pending under the user pause. No compiler,
fixture/product loader/VM/cache/scope/writer runtime, broad harness, forbidden
route, native/device/simulator/emulator/UI/capture, global process inventory,
or active loader folder was used. Prior review, frozen inputs, Git, canonical
files and sibling lanes were unchanged. No native/product process, instance,
executable or scratch checkout was created, so no such cleanup was needed.

After freezing, reproduction is read-only:

```text
python3 verification/swift-guarded-snapshot-parent-work-source146/rebind.py --check-only
python3 verification/swift-guarded-snapshot-parent-work-source146/freeze.py --check-only
```

`candidate.json` contains the scope, deltas, paths and arithmetic;
`operation-ledger.json`, `scalar-shapes.json`, `drop-surface.json`, and
`compiler-bindings.json` expose the detailed data reconciliation. The cost
interface preserves all required cuts. Every new file is confined here.
