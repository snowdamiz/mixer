# Offline resource binary correspondence

This packet advances the root-accepted source146 resource component. It does
not change its prices, select a caller multiplier, authorize a fixture run or
complete compiled standard-library correspondence for an actual executable.

The source tree is `690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`
and host11 is `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
The root acceptance, independent review and retained original LLVM are bound by
their exact hashes in `audit.py`. All frozen inputs are rehashed read-only.

One coordinated Rust 1.99.0 compiler-only query retained four function pointers
at EOF in two private modules of a scratch copy of original146. They force
`drop::<Vec<SwiftSlot>>`, `drop::<Vec<Patch>>`,
`drop::<Vec<Option<ScanPlan>>>` and `drop::<File>`. Original source bodies and
lines are unchanged. The aarch64-apple-darwin opt0/codegen1 query emits LLVM IR
only. It succeeded in 3.5502204159274697 seconds; no executable was linked or
run. Full LLVM and type-size stdout are retained losslessly, with five identity
preimages/keys. Both command children were waited and scratch was removed.
`compile-once.py` and `collect.py` are historical one-shot producers: do not
replay them. No further compiler is required to review this packet.

`correspondence.json` retains 29 LLVM functions, 16 selected installed native
functions and all selected native instruction bytes and relocations. Three
Vec wrappers pass element size/alignment 136/8, 32/8 and 56/8 to the exact
shared deallocator. SwiftSlot visits the live slice and reaches the nested
Type, DecodedInstruction and u32 vectors. Patch and Option<ScanPlan> have
trivial element teardown in this exact compilation. These observations do not
select a resource-price discount.

The File query reaches File → Unix File → FileDesc → OwnedFd, retains the
fcntl(F_GETFD=1)/errno(EBADF=9)/abort precheck and issues one ignored close.
The installed optimized FileDesc destructor has the precheck elided and directly
branches to close. Those compilation contexts are explicitly distinguished.
Selected installed read, read_buf, metadata, write and position bodies build
Os-tag2 errors from errno; the allocating File path helper returns the immutable
NUL-message object with tag0. Complete generic File open/options/path-wrapper
binding remains pending, including the source-ruled-out invalid-options branch.

Installed std/core/alloc/gimli archives and tools are fully hashed. The exact
precompiled RawVec<u8> and RawVecInner symbols were found in libgimli, using
their LLVM-declaration names rather than a crate-name assumption. Native
instructions show capacity×element_size and alignment passed to the external
Rust allocator shim, with zero capacity/size producing no deallocation request.
An independent BSD ar/Mach-O reader validates 539 emitted instruction and
relocation records against the archived object bytes. A bounded host dataflow
evaluator checks 46 native RawVec cases; it executes no native code. Twenty-four
hostile mutations fail closed, including a commented-out LLVM call that exposed
and corrected an early parser weakness. The Xcode LLVM21 default nm failure on
embedded LLVM23 is preserved; native --no-llvm-bc and already installed compatible
Rust LLVM tools required no toolchain changes.

Run the read-only review commands from the repository root:

```sh
python3 verification/swift-guarded-snapshot-resource-binary-correspondence/audit.py
python3 verification/swift-guarded-snapshot-resource-binary-correspondence/test_controls.py
python3 verification/swift-guarded-snapshot-resource-binary-correspondence/freeze.py --verify
```

The unit remains the inherited source/aggregate/destructor interface plus
native/requested-backing bytes. Private allocator/kernel/stdlib work, physical
allocation overhead, CPU/time/RSS/stack and external effects are outside that
unit and are not zero. Deallocation/close calls do not establish successful
retirement, flushing, healthy cleanup or refunds. Actual immutable
caller/build/session/executable/compiler binding, the remaining File constructor
closure, operational evidence, physical/native runtime, FieldLog, OTA and GA
remain pending. Native UI/capture/simulator/emulator tests remain paused.
