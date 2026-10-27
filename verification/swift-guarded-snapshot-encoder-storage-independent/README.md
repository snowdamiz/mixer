# Independent encoder callee storage review

Accepted within the frozen logical product-source contract: **40,531 bytes**
over **2,658 distinct slots** in **64 function/closure templates**. No blocking
product-source omission, duplicate charge, ambiguous ownership partition or
unchecked arithmetic was found in this bounded encoder callee inventory.

The reviewer imports no producer Python code. `review.py` independently checks
all 49 producer members (9,003,552 bytes), all 495 composition members, all 1,256
accepted encoder members, the root release hash and all 144 frozen source files.
The source tree is
`140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395`.
The 643 original encoder behavior lines remain byte-identical.

A fresh bounded compiler-only invocation reproduced the entire 77,320,827-byte
unoptimized MIR, SHA-256
`8c266c7d22b79965946b01015b03344776d56dde4c29a71987f3fa118613b384`.
Every selected body is identical to the producer projection. Each role was then
reconstructed from parameters/declarations/debug aliases, exact source spans,
actual types, source text, move/copy edges and lifetime markers. The retained
function hashes and source bindings identify these bodies after disposable MIR
cleanup. No encoder, VM, writer or engine function was executed.

The layout review independently decodes the three LLVM constant arrays and
checks their ordered exact type seams against all 247 measured nameable
instantiations. All seven actual Buffer substitutions were checked for each of
the four generic slot types. They have identical shapes; the single generic
source template is reused. The finite checked-u64 sum uses each actual slot once,
including zero-sized roles and natural compiler type padding. There is no
record-count factor, guessed padding, identity-size subtotal or inherited
aggregate added to E.

The independent call parser reconstructs 595 calls, including 160 direct product
calls, the indirect AccountedWasi function-item callback and all 26 actual
closure bodies. All 64 templates are reachable from the eight externally
consumed methods/functions and form an acyclic graph. Synchronous calls and
enumerated callbacks permit one live invocation per exact source template.
Loops reuse their own source declarations; their iteration counts do not
multiply storage. Sibling calls, error branches and exclusive arms are already
conservatively summed.

All 26 closure constructions were reconstructed from their captured source
roles. Eight distinct `entry!` occurrences remain distinct even though they have
the same source span/type display. Actual expression captures sum to 160 bytes;
all closure object/reference/argument/move slots sum to 416 bytes already inside
E. Neither number is an extra additive term. The entry arms are exclusive; the
parameter-range callback follows the entry callback, and the final result
closure follows the chosen arm. No product closure escapes into an outstanding
callback after the enclosing synchronous call.

One nonblocking metadata finding remains: the producer's `call-sites.json`
truncates the displayed Option::map target at a function-pointer return type.
The full MIR statement retains `AccountedWasi::snapshot_configuration_v2`, its
callee roles are present, and the independently reconstructed graph includes the
edge. `review-results.json` retains the complete corrected target. This is a
display/parser defect in the audit index, not missing storage.

The ownership partition is explicit and acceptable for this contract. Encoder
return-expression slots and by-value/reference parameter slots are included:
borrow_snapshot Result 32 bytes and initial reference 8; into_cursor Result
2,600 and owned view argument 24; next_block Result 32, cursor reference 8 and
transfer reference 8. FileIdentity::encode separately includes its 64-byte self
parameter and 64-byte return slot. These are distinct source roles even where
a compiler can physically reuse memory. External guard/proof/provenance owners,
borrowed heap payloads, the caller's 4,096-byte transfer owner, and caller-owned
Result/pattern/view/cursor/block/move roles remain outside E and require their
own integration accounting. EncoderInit/Block/Caller shape aggregates and the
52/58 identity sums must be replaced rather than added.

Thirteen independent mutation controls passed, including a zero-sized role
omission disguised by replacement, equal-count ownership overlap, an equal-total
size swap, a same-size wrong type, fabricated move evidence, loop multiplication,
return-role reassignment, inherited aggregate insertion, changed source hash,
plausible wrong source column, omitted generic alternative, recursive invocation
and u64 overflow. These checks go beyond replaying the producer validator.

`compiler-receipt.json` records the exact compiler command/version/hash, frozen
source binding, 55-second deadline, successful exit, output and owned-child
reaping. `cleanup.json` records removal of the owned MIR. `review-results.json`
records the Python command/version, output, source bindings and limitations.
Run `python3 verification/swift-guarded-snapshot-encoder-storage-independent/review.py`
to repeat the host-only frozen-packet checks. The fresh compiler receipt is
historical evidence on replay; a new independent compiler run requires a fresh
owned output destination.

This review covers the 495/144 frozen input only. It does not accept a later
authority-source correction, a complete storage floor, operational admission,
writer execution or GA. Physical stack/RSS, ABI/unwind/spills, private standard
library frames and immutable static pointees remain outside the logical source
contract. Native/device/simulator/emulator/UI/capture checks remain paused.
No process inventories, Git/canonical mutations, publication or runtime tests
were performed.
