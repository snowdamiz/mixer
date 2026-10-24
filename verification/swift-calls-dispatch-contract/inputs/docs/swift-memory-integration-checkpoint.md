# Private Swift memory integration checkpoint

Root accepts and integrates the original-owner Load/Store development slice.
Eight VM files change. The independent MR01 correction review passes 700
bindings and the producer passes 563; all 4,792 preceding positions remain,
with eight separately named unit promoted positions adding exactly 64 bytes.
The resulting accounting inventory has 4,800 positions. No runtime algorithm,
state owner, ticket limit or memory ceiling changed for that correction.

The reviewed candidate closure is
`a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b`.
Root removed four trailing spaces from each of two otherwise empty lines in
`experimental/execution/mod.rs`, as requested by review note IN01. This is the
only source difference from the reviewed candidate. The integrated 123-file
closure is `17f9ea5b93fbc0b5bd51df8484e30e0cbe420eac646730da7d330c4b4ecde9ff`.
The exact patch and both manifests are retained; the normalized candidate was
compiled and exercised after application to the checkout.

Fresh root all-feature Release runs pass 62 focused memory/frame/value/control
unit tests and 16 Frozen integration tests, serially. The actual Swift-only CI
Clippy command passes with warnings denied. No tests were skipped. Rust/Cargo
1.99.0, macOS arm64, exact commands, source identities, outputs and owned build
scratch cleanup are retained in
`verification/swift-memory-root-integration/integration.json`.

The byte-bound producer evidence includes 64 memory selections across Swift-only
and all-feature Debug/Release, 184 preceding frame/control/value selections,
four canonical MIR configurations, sixteen paired typed layouts and eight
library checks. Independent correction review freshly executes twelve focused
bound selections, one unit MIR and two typed layouts; its 39 Frozen-method
identities, 56 paired Frozen observations and four 16-test integration runs are
explicitly reused evidence. Root's 16-test integration run above is fresh.
The earlier behavior review's 24 additional adversarial selections remain
preserved. Named-object accounting does not measure compiler stack or RSS.

The integrated private caller obtains the instruction through the actual retained
frame pin, ends its immutable view before mutation, charges one instruction and
one caller work credit, and advances the PC once. Helpers share the Frozen
Load/Store algorithm. They check opcode, type and operand floor before pops,
preserve exact error prefixes, keep post-pop cleanup debt, and publish into the
original fixed result slot. Outer successful publication does not imply a
successful inner memory result. Original first-failure, terminal drain and pin
retention rules remain enforced.

This accepts no full dispatcher, copy/fill/size/growth, host/WASI join, Ready or
public invocation. The existing absent-cursor Cleanup diagnostic remains open
under G08. Native joins, immutable published FieldLog from a separate repository,
physical phones, signing, store, customer, operational and GA acceptance remain
pending. No native instance or physical device was used for this receipt.

Run the read-only acceptance checker:

```sh
python3 -B verification/swift-memory-root-integration/verify.py --live
```
