# Guest-UI native validator host receipt

This slice adds only `mixer_vm_capability_guest_ui_validate_v1` and its fixed
signature helper. It uses complete existing capability validation with the
fixed startup, then inspects that same validated module. There is no instance,
session, mailbox, registry reservation, startup, native I/O, new parser, or
execution route in this operation. Existing source methods retain their bytes;
the four implementation diffs contain 82 additive lines and no deleted lines.

`receipt.json` captures commands, tool versions, source revision and source
manifest, output hashes, archive hashes, and unchanged frozen contract/header
hashes. Debug and Release each passed 79 Rust tests: six new guest-UI tests and
73 existing capability/native/core tests. The independent public-header C
client compiled, linked and ran 16 ABI/export/preflight/full-registry checks in
each configuration. Its startup deliberately traps if executed; validation
succeeds without consuming fuel or making host calls.

`supplemental-receipt.json` records six new tests per configuration with exactly
the native-only feature, plus 49 default library/interpreter/session tests per
configuration. `fixture-manifest.json` hashes 17 deterministic fixture binaries
and records the deliberate Wasm types/imports/instructions. The fixture source
and C client are original independent encoders, using no VM fixture builders.
Root review of this source and fixture manifest remains pending.

`symbol-gating.json` records current-source direct-rustc default and guest-only
object compilation and symbol inspection. Those objects exclude both native
capability validators. This is object symbol evidence, not a rebuilt default
package archive. Combined native archives were separately linked by the C
client; supplemental work confirmed their exact hashes did not change.

The caller-thread allocation probe observed validation: 47 allocations, zero
retained requested bytes, peak 2,806 bytes, largest 368 bytes. The construction
positive control observed a 2,097,152-byte allocation for 32 memory pages.
These are requested allocation sizes, not allocator overhead, process heap,
RSS, or mobile memory evidence. Existing core allocator abort boundaries remain.

The selected Release archive is
`vm/target/stream-validation-verification/release/libmixer_vm.a`, SHA-256
`5358e39b9efb0561d185c4c22152df057a78a2ca43c582e7b5493e5877fe23e4`.
The Debug archive hash is
`101899244d9764079a2dd8afff5995acda8a9fedcc5b7ff2d0c5eb357a9e6b57`.
Both use the one combined stream/cache/native feature graph. The bridge lane
was given the Release selection; frozen native package pins were not edited.

The first recorder attempt is retained under `attempt-1/`. Its Rust tests and
C compile/link/run passed. Apple `nm` returned 1 when reading newer LLVM23
attributes in Rust standard-library archive members. Final inspection uses the
linked Mach-O executable and passed. This tool compatibility failure does not
become a passed archive-inspection claim.

This evidence is macOS host validation only. Runtime UI headers, documents,
events, signed selection, presentation, Swift guest compilation, simulator and
physical iOS/Android, published FieldLog packages, signing/store/customer review,
and every GA gate remain outside this native slice. Phones remain disconnected;
no new physical-device discovery or run was attempted.
