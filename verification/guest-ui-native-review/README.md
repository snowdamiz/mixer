# Independent native guest-UI validate-only review

Result: no actionable finding in this bounded native slice. This is macOS host
review evidence, not UI integration, mobile, release or GA acceptance.

The source path is the existing complete capability validation followed by
inspection of the same validated module, at
`vm/src/experimental_capability_guest/mod.rs:271`. It retains the v3 grammar,
approved imports, module/memory/resource ceilings, body type validation and
fixed void completion export. It checks the three required exact function
names/signatures and non-imported indices. The stricter i32 startup result uses
the unchanged `capability_export` error helper with no function and offset zero.
No instance, mailbox, session, registry reservation, startup or native I/O call
appears in this path. Its temporary `Module` is dropped on return. Numeric
preflight includes every module/config/report range before any output write;
the existing unaligned config reads, report writes, statuses and panic boundary
are reused. All four implementation diffs are additive; existing validate/create
bodies, old headers and feature declarations retain their bytes.

The independently authored `public_probe.c` includes only the public C header.
It encodes its own core Wasm binaries and links the exact selected combined
Release archive. Its 135 checks passed across the three exports and twelve
signature shapes, missing/exact-name/global-kind/import aliases, malformed and
unsupported uncalled bodies before export rejection, forbidden start section,
missing/multiple/shared memory, report aliases at both range ends and contained
within a read range, unaligned fixed structures, and validation while sixteen
actual capability sessions fill the shared registry. Every function body in
its ordinary module deliberately traps if executed; successful validation uses
zero fuel and host calls. Legacy startup validation still accepts the existing
void/i64/f32/f64 no-argument forms. Defined-only rejection includes an imported
checkpoint matching the completion signature, with other required import aliases
rejected as well. No fixture or builder from the implementation tests is used.

`audit.py` checks the supplied primary and supplemental receipts, complete source
manifest, command/log digests, frozen contract/header digests, retained archive
and linked binary digests, earlier failed attempt receipt, fixture source/capture
digests and symbol-gating logs. It confirms the current source remains identical
to that manifest after the independent probe. The owner logs contain, per Debug
and Release, 79 combined native tests, 6 native-only guest-UI tests, and 49 default
regression tests with no failures. The default/guest-only object symbol logs
exclude both native validators; selected Debug/Release linked executable symbol
logs include them. The exact review commands, tools, outputs, source revision
and all input hashes are in `receipt.json`.

The original caller-thread allocation test was read and its exact source/log
digests checked. Its 32-page validation reports 47 requested allocations, zero
retained requested bytes, 2,806-byte peak and 368-byte largest allocation. Its
construction positive control requests 2,097,152 bytes for instance memory.
Together with source inspection and validation while the registry is full, this
supports the claim that the validator creates no instance/mailbox/registry owner.
These allocation measurements were not independently rerun here; they exclude
allocator overhead, heap/RSS, other threads and device behavior. Existing core
allocator abort boundaries remain.

The retained selected Release archive is
`vm/target/stream-validation-verification/release/libmixer_vm.a`, SHA-256
`5358e39b9efb0561d185c4c22152df057a78a2ca43c582e7b5493e5877fe23e4`.
The reviewed owner receipt is
`96db9cca2bcf850cd5de54e59b1f96298a0645d1d4a6c13186d5e662e49c2e06`;
the supplemental receipt is
`6332431cef0e815c3437e003ce9193194be72ac1da238449590cea6c56b85614`.
No archive, package pin or production source was changed by this review.

No full native graph was rebuilt; retained owner tests are audited evidence.
Default/guest-only symbol evidence is direct-object evidence, not rebuilt package
archive evidence. This review does not validate runtime UI control headers,
documents, event content, bridge scheduling, signed installation, native
presentation, Swift guest compilation, published FieldLog consumption, signing,
store or customer review. No devices were queried or run; disconnected physical
iOS/Android gates and all unmet product/GA gates remain pending.
