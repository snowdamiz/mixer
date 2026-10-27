# Source146 native, path and teardown interfaces

This frozen source/interface candidate replaces the unspecified native-open and
native-error cuts with checked parameterized prices. It also supplies an
explicit conservative amendment for the positive-only host-storage inputs. It
selects no actual root, fixture, path, identity, policy, quote or grant. Compiled
standard-library correspondence is a separate condition; the concurrently owned
binary-correspondence packet was neither read nor changed.

The exact source146 tree is
`690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`,
and host11 is
`027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.
All146 source-map members,11 original support members, the accepted child,
storage and resource receipts, and six complete frozen dependency packets are
rehash checked. The original source146 layout output is decompressed and
rehashed without compiling; its exact Error8/alignment8 and File4/alignment4
records are retained. These widths describe inline values, not heap resources.

Nine additional official Rust files are retained at
`b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, matching the previously qualified
Rust1.99 compiler. For Darwin's `stat` and primitive ABI declarations, the exact
Rust Cargo.lock selects libc0.2.183. Its official immutable crate download is
verified against lock checksum
`b5b646652bf6661599e1da8901b3b9522896f01e736bad5f723fe7a3a27f899d`;
nine selected source/license members are retained. This is archival platform
source evidence, with MIT/Apache notices, rather than an engine or runtime
dependency. No installed toolchain or existing dependency list was changed.

The unit remains source/aggregate/destructor-interface occurrences plus
explicit native operand sizes and requested-backing allowances. Seventeen named
public interface records and751 fixed native bytes, plus seven copies/reads/
request extents of the actual encoded path length `n`, give:

```
native_open(n) = 768 + 7*n
error_native = 3 interface events + 20 native bytes = 23
entry = 119922 + 24 + sum(native_open(n_i)) + 23 + 53*1210256815
      = 64143735004 + 7*sum(n_i), for the five actual setup paths
```

The source146 calls are three read-only opens for input/build/session, then two
write/create_new opens for rows/snapshot. There is no truncate request. An
ordinary failed open terminates setup, retains every earlier File and the
original Error, and creates no File for the failed stage. Five successful setup
opens are distinct from the loader's later executable open. Alternative success,
NUL-error, errno-error and temporary disposal records are conservatively summed;
the price does not assert that all branches run.

The standard source uses `cvt_r` to retry an interrupted native open with no
attempt ceiling. Accordingly this packet prices one **public semantic native
open interface**, not a bounded count of underlying `open` syscalls. There is
no finite private-retry, CPU, kernel, scheduler, allocator-implementation,
physical-stack or RSS claim. Every evaluator output exposes this boundary.

`PathExtent` requires each immutable actual encoded length `n`, independently
bound P0 backing `B >= n`, and a custody obligation. There is no4096 setup cap.
Unix OsStr bytes are passed unchanged, including non-UTF8. Empty input still
produces a valid one-byte C string and lets the OS decide the open result.
Interior NUL causes the borrowed static InvalidInput error before the public
native open. The threshold is precisely384: `n < 384` uses a384-byte inline
MaybeUninit array and requests zero heap bytes; `n >= 384` allocates a Vec with
capacity `n+1` **before** NUL validation. A long NUL failure drops that original
NulError Vec and returns the static error. On a valid long path, adding the NUL
fits the already requested capacity; equal capacity/length bypasses Vec shrink,
and CString/Box later deallocate the same existing backing. Global exposes
exactly the requested layout, with no physical allocator-size inference.

CString's infallible `with_capacity` can invoke an allocation failure handler.
That is not a returned `io::Error` or a healthy setup-refusal receipt. The finite
layout-return contract rejects `n >= isize::MAX`; checked u64 quote arithmetic
also refuses overflow. Private OOM/panic hooks and unwinding infrastructure are
outside this unit, with no fabricated bound.

The original observer gives executable-path first-NUL position `1 <= e <= 4095`
in its caller4096-byte buffer. The separate executable open therefore has price
`768+7e <= 29433`, with CString requested heap at most4096 bytes. The frozen
storage interface's4097-byte executable conversion envelope remains a safe
conservative allowance. That observer bound is never applied to setup paths.

The complete original P0 binding is at least512 bytes: five fat path references,
256 claims bytes,40 original validator-limit bytes and136 product-limit bytes.
All path pointees remain separate. `p0_bounds` requires the actual whole binding
extent and a complete typed immutable identity/diagnostic pointee roster, each
with an independently bound extent and backing. Source-length arithmetic does
not select, synthesize or authenticate the root's eventual bytes. Empty paths
and zero extents are modeled accurately here; the frozen adapter's positive-only
input restriction is not silently asserted to prove those extents positive.

`interface-derivation.json` retains the complete Darwin repr(C) stat field layout
(144 bytes), fixed errno pointer/c_int interface, original File read/fstat/lseek,
SHA256 and process-observer operand records. Native output buffers are caller
provided. The observer, loader File read/metadata/position and hash helpers make
no additional explicit owned-backing request; their private implementations are
outside the unit. Existing retained byte vectors and the hash/output arrays are
already accounted owners, rather than newly allocated native temporaries.

The accepted closed type/resource graph covers20 returned/entry/leaf body rows
and13 constructor/internal rows, including all64 nested SwiftSlot element
frontiers. All reachable product destructor callbacks are closed; plain vector
elements contain no resource fields. File follows FileDesc/OwnedFd and only
checks/closes; Arc<AtomicBool> visits AtomicBool and implicit Weak then frees
its existing24-byte allocation; Global Vec/Box teardown visits initialized
elements and deallocates original backing. The exact actual Error route can
only contain inline Os or borrowed static-message tags. Valid fixed open options
exclude custom option Errors, actual File Read/Write excludes foreign callback
errors, and no Error formatting is introduced. Custom Error, custom allocator,
foreign resource and arbitrary callback provenance fail closed.

Thus **the exact additional explicit requested heap is zero** for File owned
resources, retained closed Error backing, loader native helpers and the complete
transitive payload teardown graph. Existing Vec/Box/Arc backing freed during
teardown is not an extra allocation. The source claim does not promise close,
flush, descriptor retirement, destructor completion or a host refund.

`storage-interface-amendment.json` explicitly retains the positive-only adapter
using source-derived native operand envelopes:

| Frozen storage input | Conservative interface bytes | Extra requested heap |
| --- | ---: | ---: |
| File each |73|0|
| closed Error each |32|0|
| loader native temporary union |8572|0|
| uniform complete payload teardown union |29394|0|

File73 and Error32 are the complete accepted native operand-record sums. Loader
8572 sums the ten concrete helper interfaces, including borrowed fixed buffers
as deliberate conservative coverage. Teardown29394 is the maximum across all33
complete typed interface unions (SnapshotRunV1), including nested element
interfaces and whole typed input extents. These are positive logical operand
allowances; they are neither allocated byte observations nor measurements of
physical stack. Existing inline/buffer extents may be conservatively covered
again in this explicit amendment. No4-byte descriptor or arbitrary1 replaces a
resource, and no destructor **work** price is substituted for storage.

The fixed route's Error count is396924. Complete original caller, leaf, loader
frame unions plus accepted product retention total3175386 bytes. Each distinct
simultaneously owned Error occupies8 disjoint inline bytes; dynamic byte/plain
vectors, Boxes and AtomicBool introduce none. `floor(3175386/8)+1` conservatively
bounds all such owners, plus one standard helper's original in transfer. This
intentionally overcovers all non-Error bytes and overlapping retained envelopes.
It does not infer one Error from an aggregate field or use the53 work visits.
Any future outer-parent/foreign Error owners require their separate P0 bound.

Pure controls pass7 methods and836 assertions. They independently enumerate
per-byte record extents, test empty/nonUTF8/interior-NUL paths,383/384 and long
boundaries, all five setup-failure prefixes, separate executable ownership,
complete P0 inputs, source zeros versus operand allowances, Error count,
monotonicity, missing/unknown input, hostile contract mutations and overflow.
Checker failures are preserved: the source-reference map was initially assumed
to repeat its manifest tree field; empty scalar resource rows were initially
rejected; and two extra Vec-drop source anchors used an older generic spelling.
They changed no frozen input and executed no product.

Reproduce without changing the frozen packet:

```
python3 -B verification/swift-guarded-snapshot-native-interface-bounds/derive.py --check-only
python3 -B verification/swift-guarded-snapshot-native-interface-bounds/test_interfaces.py --check-only
python3 -B verification/swift-guarded-snapshot-native-interface-bounds/freeze.py --check-only
```

All writes stay in this assigned folder. Python children are bounded, waited and
checked only by their owned process-group IDs; failures, source snapshots,
commands, Python version, source/tree bindings and raw stdout/stderr are retained.
No compiler, product, fixture, loader, constructor, leaf, VM, UI, capture,
simulator/emulator, global process inventory, Git mutation, production action,
external message or credential change occurred. Native runtime remains paused.
Independent review, root selection of the explicit amendment, compiled standard
body correspondence, actual immutable caller/build/session/executable binding,
complete whole-host work/storage funding and execution/retirement, FieldLog,
OTA, operational and GA gates remain pending.
