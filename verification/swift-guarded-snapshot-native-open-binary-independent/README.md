# Independent native-open compiled-interface review

No blocking finding was found in the exact frozen candidate
`7b5762f1955fefa2060b0d4fdb4dd393cb8b38c94078159ddf6bc538a22c67f5`
(112 members, 2,855,785 bytes), released by root receipt
`f29e7b47e5be01e24cccdf8474ddc5c76bdc1ba0d071197970b9310bff83a6ed`.
This review supports conditional selection of the constructor interface only.
Root acceptance remains separate.

The independent helper imports no producer code. It reparses installed BSD ar
archives and Mach-O headers, symbols, sections, raw instruction bytes and full
relocation records. It checks all seven body extents through the next text
symbol, all 438 words and 46 relocations, the static NUL record and its relocated
42-byte message. Active assembly annotations are ignored. The separate integer
AArch64 decoder and evaluator reject unknown opcodes, calls, indirect targets,
and unimplemented relocation addends. Raw words and relocations authorize the
offline model. A separate LLVM evaluator follows connected active statements;
comments cannot establish a store, argument, pointer, branch or call.

`source-compiler.json` rechecks source146, every source reference, the exact
646-byte append, compiled manifest/tree, counted argv/environment bytes,
fingerprint environment, original flags, installed compiler/tool/library bytes,
and historical output/cleanup receipts. The assignment's earlier 670-byte
description is not the retained append length. The retained predeclared plan
contains the exact 646 bytes and hash, and matches the compiled manifest. The
installed Rust1.99/LLVM23.1.1 optimized standard library stays distinct from the
one opt-level-0 wrapper query. Neither the inherited host context nor a future
outer composition is automatically rebound to an actual immutable caller or
executable by this review.

`critical-contracts.json` records independently decoded operands and the algebra:
short n<384 uses source scratch384 (physical frame496 is separate); long paths
request n+1/alignment1 before NUL validation; selected CString capacity n+1 skips
reserve and shrink and preserves its original pointer; normal callback and
NulError paths free that backing once. Valid CString destruction clears the
first byte before free; the NulError Vec drop preserves its original bytes.
The synthetic callback landingpad also clears/frees once before unwind resume.
Selected read and write/create_new defaults exclude both dynamic Error::new
branches; static NUL and errno tag2/shift32 representation are checked. The
inherited logical interface remains 768+7*n and Error-native23, without a new
policy or pricing grant.

The independent run covers 274 full paths, 10,488 core-CStr cases over eight
alignments and every first-NUL position at selected lengths through385, 1,152
option/custom-flag/mode combinations, 16 finite retry traces, three capacity/OOM/
synthetic-landingpad cases, ten generic LLVM routes, and seven sparse same-backing
constructor cases including a representable arithmetic boundary. All438 words
decode. The main synthetic suite observes367 instructions and400 of479 listed
intrabody edges. `frontier.json` lists every instruction, branch successor,
direct call site and both indirect-call contracts, with observation at each
actual call site. Unobserved growth/shrink, small borrowed-CString specialization,
dead result branch, and exception edges remain explicit; no test coverage is
claimed for them. 39 independent hostile controls reject active operand, word,
raw-relocation, static-data, alignment, flags, error-tag, normal/unwind-destruction,
unknown-call/opcode/relocation, and LLVM mutations. Two positive controls show
that injected native/LLVM comment decoys leave active traces unchanged.

The producer's pure-host `review.py --check` and `freeze.py --check` both pass.
Their original seal is unchanged. All independent failed attempts are retained
under `commands/` with exact helper snapshots, command/environment/tool/source
digests and stdout/stderr. They corrected reviewer harness issues: an ambiguous
symbol substring, zero-filled scratch masking a missing terminator, and an
initial missing rejection for unsupported relocation addends. The final helper
uses an exact symbol, poisoned scratch and explicit fail-closed addend checks.
The producer's prior post-CString-drop observation failure and exact two-pyc
cleanup incident remain preserved in the frozen input and rehashed here.

Allocator, memchr/memcpy, libc, kernel, OS classifier, panic/OOM and unwinder
implementations are explicit external interface boundaries. Finite retry tests
prove no retry bound. Synthetic landingpad entry proves no actual unwind-table
selection or healthy cleanup. Actual P0/path/identity/diagnostic pointee extents,
immutable caller/build/session/executable binding, pricing authority, successful
fixture, healthy refusal/cleanup, native/device/store/customer/operational,
FieldLog published-package, OTA and GA evidence all remain pending. No compiler,
disassembler, product/runtime/native/UI/capture, Git, global process inventory,
or other-lane mutation was performed by this reviewer.

Read-only replay after freeze:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-native-open-binary-independent/independent.py --check
PYTHONDONTWRITEBYTECODE=1 python3 -B verification/swift-guarded-snapshot-native-open-binary-independent/freeze.py --check
```

Do not replay the producer's one-shot compiler/disassembly helpers or its
`run_checks.py`. `run.py` creates attempt records and must not be replayed into
this review after it is sealed.
