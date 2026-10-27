# Independent frozen resource binary review

The released candidate is
`verification/swift-guarded-snapshot-resource-binary-correspondence`, seal
`58f49d3bcc844678bef604bc4989e81b2bfea758b300ca3158b229a510018f1d`:
116 members, 2,151,908 bytes. The release document hash is
`f01317a2b7d59c719bb16a71a922b6781ceeafe62adb82eeccf3c5389013e91c`.
The candidate and all referenced evidence remain read-only.

This review supports the selected compiled correspondence in its stated
interface/requested-backing unit. It selects no root acceptance, caller
multiplier, price change, runtime grant, private implementation bound or GA gate.

The independent checker reconstructs all 146 source members and the two exact
EOF appends; checks host11 and all five compiler identity preimages; binds the
four emitted `llvm.used` pointers through their `std::mem::drop` bodies; and
checks the 29 retained LLVM excerpts against the lossless LLVM output. Active
call operands, length offsets and normal/unwind branch destinations are checked.
Three Vec specializations pass size/alignment 136/8, 32/8 and 56/8. SwiftSlot
reaches Type, DecodedInstruction and u32 vector teardown. The two other selected
Vec element drops are trivial in this exact query. Existing prices stay intact.

An independently written BSD ar/Mach-O parser rehashes installed
std/core/alloc/gimli archives and checks 453 instruction records plus
86 relocations, totaling 539. This census includes ten padding NOPs. The 16
selected native symbols are a selected-symbol count, not 16 disjoint behaviors.
The exact external LLVM RawVec declarations resolve to the defined installed
libgimli symbols. A separate ARM64 word evaluator reproduces all 46 producer
cases and 50 additional valid, nonoverflowing-layout/pointer cases. Its allowed
instruction set fails closed; finite probes are not a universal proof over
invalid Rust layouts or arbitrary ARM64 code.

The opt0 LLVM File teardown traverses File, Unix File, FileDesc and OwnedFd. It
retains fcntl command1, errno comparison9, the diagnostic formatting/Result drop
and abort branch, followed by one ignored close request on its returning path.
The installed optimized FileDesc has only a descriptor load and close branch.
These contexts are distinct. Neither body establishes successful closure,
flushing, retirement, healthy cleanup or a refund.

Six selected installed error bodies decode errno into the Os tag2 representation;
the independent checker reads the ORR operand bits, not its assembly annotation.
The static NUL error message has length42, ErrorKind20, an immutable data
relocation and pointer tag0. Its enclosing Result discriminant1 is a different
field. The allocating helper's dynamic callback path is not closed by this
static branch. Generic/injected Custom errors remain refused.

`findings.json` preserves seven producer semantic-helper coverage gaps and the
reviewer's own failed development attempts. The producer's original 24 hostile
controls pass on replay. All 29 independent mutations are refused, including
the seven accepted by isolated producer helpers. The full frozen hash/object
custody would reject data substitution; helper gaps are not evidence of a false
frozen body. Root can select the exact independent predicates as amendments
without modifying the original packet.

Complete generic File::open/OpenOptions/stack path-wrapper constructor closure,
including the source-ruled-out invalid-options branch, and actual immutable
caller/build/session/executable/compiler-context composition remain pending.
The unit excludes private allocator/libc/kernel work, physical allocation
overhead, CPU, time, RSS and stack. Those quantities are outside the unit and
are not zero. No product or native code was executed. UI, capture, simulator and
emulator runtime remain paused; FieldLog, OTA and GA remain unaccepted.

Replay from the repository root:

```sh
python3 -B verification/swift-guarded-snapshot-resource-binary-independent/run_checks.py
python3 -B verification/swift-guarded-snapshot-resource-binary-independent/freeze.py --verify
```

`command-receipt.json` records the exact review command, Python version, input
digests, stdout digest and observed scope. No compiler, disassembler, native
runtime, UI/capture process, global inventory, Git change or toolchain change is
performed by the reviewer. Python bytecode writes are disabled; this lane has
no disposable native instances or scratch children to retire. Historical
candidate compiler cleanup remains a historical receipt, not a new observation
of whole-machine process state.
