# Independent frozen native-interface review

The source/interface candidate passes independent offline review, conditional
on explicit root selection of its proposed operand-allowance amendment. This
packet recommends that amendment and does **not** select it, grant a root policy,
or qualify actual caller data or execution.

Reviewed candidate: `verification/swift-guarded-snapshot-native-interface-bounds`,
seal SHA256 `d02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f`,
115 members / 1,255,928 bytes. The root release is independently bound by SHA256
`bcb2ce93d57fc74b968e979fb81947fc0d24ce12f689ae17df1b41e32255e313`.
Source146 is `690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185`;
host11 is `027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2`.

Independent checks pass **8 methods / 9,579 assertions**. They rehash the whole
candidate, all six named frozen dependencies, source146, host11, the three
accepted root receipts, all 19 inherited platform-source references, four
resource follow-up Rust references, nine additional Rust references, and nine
selected libc source/license members. The exact Rust lock binds libc0.2.183 to
its recorded archive checksum. The complete crate archive is not retained here;
this review verifies selected members and that frozen receipt/lock binding,
without making a new download claim.

Seventeen native-open events plus 751 fixed operand bytes and seven extents of
encoded path length give `768 + 7*n`. The Error interface is `3 + 20 = 23`.
The entry expression independently folds to `64143735004 + 7*sum(n_i)` for five
setup paths. Those calls are three read opens and two write/create_new opens;
an ordinary failure retains the successful prefix and the original Error.

The precise Darwin path threshold is 384. Short paths, including empty input,
use the fixed inline scratch. Long CString conversion requests `n+1` bytes
before NUL validation; long NUL failure drops its original Vec. Unix non-UTF8
bytes are valid inputs. The loader's separate executable path has
`1 <= e <= 4095`, so its public-open price is at most 29,433 and its CString
request is at most 4,096. This supplies no setup-path cap. Archived exact
source146 layouts retain Error8 and File4; the independent Darwin repr(C) stat
layout is144 bytes.

The positive amendment is source-backed **operand coverage**:

| Input | Operand allowance | Additional explicit requested heap |
| --- | ---: | ---: |
| Each File | 73 | 0 |
| Each closed Error | 32 | 0 |
| Loader native helpers | 8,572 | 0 |
| Uniform complete payload teardown | 29,394 | 0 |

The root must explicitly permit these conservative operand allowances in the
positive-only storage interface. These are neither observed heap allocations
nor physical stack bounds, arbitrary positive constants, or destructor work
prices reused as storage. Existing backing is released rather than newly
allocated. The independent traversal binds 105 declaration fragments, traces all
14 vector element frontiers, retains all three nested vectors for every one of
the 64 SwiftSlot elements, and recomputes all 33 complete typed unions.
SnapshotRunV1 is the maximum at29,394 bytes.

Complete caller311,071 + leaf320,766 + loader644,008 (including validator frames)
+ retained product1,899,541 =3,175,386 bytes. Every distinct simultaneously owned
closed Error requires eight disjoint inline bytes; byte/plain dynamic elements
introduce no additional Errors. Thus `floor(3175386/8)+1 = 396924` conservatively
overcovers the authored graph and one helper original during transfer. It uses
no operation/visit multiplier. Foreign Error callbacks or future outer-parent
owners require separate P0 bounds.

The public semantic-open unit does not bound private EINTR retries, syscall
count, CPU, time, kernel/allocator internals, RSS, physical stack, OOM or panic
hooks. Infallible CString allocation failure is not returned io::Error or healthy
refusal. Custom resources, custom Error provenance and allocators are excluded.
Actual whole P0/binding extents, complete immutable identity/diagnostic pointee
rosters, actual paths, file/build/session/executable identities and caller
correspondence remain pending. Nonempty custody labels cannot authenticate them.

`commands/` preserves all five own checker attempts and exact source snapshots,
commands, Python version, stdout/stderr and waited child-group receipts. The
first three attempts failed on review-harness assumptions about Path versus
string sorting, comment-elided declaration hashes, and explicitly renamed
Span/Resource declarations. Attempts04 and05 passed;05 adds independently
retained allocation/deallocation and ABI anchors. The candidate's four failed
attempts remain intact. No failed receipt is promoted.

No compiler/product/fixture/native runtime, UI/capture, simulator/emulator,
installed toolchain, live source, other active lane, Git, network or global
process inventory was used or changed. Every owned pure checker child was
waited and its own process group checked absent; no other project was touched.
Native runtime remains paused. Binary correspondence is independently active
elsewhere and was not read. Actual execution, healthy cleanup/refunds,
FieldLog, OTA, operational and GA gates remain unverified.

The final `review.json` is the structured recommendation;
`independent-derivation.json`, `independent-source-evidence.json` and
`input-bindings.json` retain the independently recomputed arithmetic, full type
union roster, extra source anchors and exact read custody. Replaying
`python3 -B verification/swift-guarded-snapshot-native-interface-independent/review.py`
recomputes these deterministic review outputs without changing frozen inputs.
The freeze checker is available as `freeze.py --check-only`.
