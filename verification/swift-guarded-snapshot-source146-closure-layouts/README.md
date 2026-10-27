# Original source146 anonymous closure layouts

A single bounded compiler-only build adds three #[used] function pointers at
the ends of two files. They force SnapshotAdoptionV1's original generic core
and the original Bytes<4096>/Bytes<16384>::put instantiations. All146 original
source bodies, original lines and closure expressions remain unchanged.
No executable is linked or run. Rust1.99.0 aarch64-apple-darwin emits LLVM IR
and print-type-sizes data successfully in2.715 seconds. Both complete outputs
are retained as lossless gzip archives. The compiler was waited, its owned
group was absent and all owned source/output scratch was removed.

The actual outer core closure is64 bytes aligned8, consistent with the eight
real captures found by independent MIR review. The earlier callee query roster
omitted one capture and remains preserved unchanged as a finding. The three
inner borrowing closures are16 bytes aligned8. The atomic try_update closure
is genuinely zero-sized with alignment1. Bytes::put's closure is8 bytes aligned8.
These are direct original-expression compiler observations, not capture proxies.

`verify.py` rechecks the original source map, all append-only compiled hashes,
five compiler identity keys, complete raw-output archives and exact original
closure span records using a separate parser. Consumers must review role and
generic-specialization applicability. LLVM is retained as compiler evidence;
this packet does not claim full std binary correspondence, whole-host funding,
actual fixture execution, healthy cleanup or GA qualification. Native runtime
remains paused. Do not replay the one-shot query.py.
