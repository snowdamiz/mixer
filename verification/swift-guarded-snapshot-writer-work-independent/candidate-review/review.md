# Independent review of the frozen writer/control/wrapper proposal

Disposition: **ledger completeness corrections required**. This review does not
accept the local work interface or select operational work. Three omissions are
reproduced in `findings.json`. They are small source-action defects; a numerical
failure of the full proposed inequality has **not** been established. In particular,
large mutually exclusive terminal-copy allowances can dominate a late Deadline
path. An omission and a disproven aggregate bound are different conclusions.

The target is the original frozen 495-member composer, seal
`bf17889754e7ef436fababcf8b96f5109285f982bcc48258a0b9e204a95b1751`,
with 144-source tree
`140761754a158c72209120de9ac5f78f7a1d5c20c3cddd6deeb9fff7a2d1b395`.
All 495 sealed members, all 144 source members, and the producer's 121 exact
definitions and declaration contexts were independently hashed. The producer's
14-member seal and explicit root release match the assigned digests. Exact
definitions are bound by the producer binding file verified under that seal;
`input-custody.json` records its independently reproduced definition-tree digest.
No current canonical source or later correction was substituted.

The six-member preaccess seal, its criteria, source custody, receipt, and recorded
812 controls were read and verified as **predecessor evidence**. Those controls
were not written or rerun by this reviewer. This packet adds its own independent
Python controls. It imports neither predecessor nor producer scripts. No VM,
engine, writer, Rust compiler or native runtime is executed.

## Method and findings

The manual review reads actual frozen function bodies and applies the accepted
logical-action convention: named place fetch/store, scalar operation, carrier,
decision, repository entry/return, explicit aggregate slots, and explicit bytes.
The byte lexer only verifies custody; it does not authorize execution or OTA.
Finite tests check arithmetic and source-sensitive adverse event envelopes;
matching source text is not a behavioral runtime test.

1. At `cache/initial_profile_v1.rs:450`, the writer's actual-count expression has
   cache reference fetch1, proof9, count getter46 and result binding1: **57**.
   Its producer row is56 and omits that binding.
2. The first identity loop in both cache and WASI pairing needs the
   `&self.buffers` field borrow/fetch1. The loop rows185 and246 contain only
   setup2 plus three/four iterations of61. They become186 and247. The separately
   priced receiver for `.iter().zip(...)` is a distinct later occurrence. The
   WASI pair becomes667; its embedding plus the cache's own omitted fetch makes
   the cache pair1930. Finish bookkeeping inherits the WASI increment.
3. `snapshot_observe_stop_v1` has a success upper15. The last Deadline path uses
   the same14 preceding actions, then origin fetch1, Deadline tag1 and Err1:
   **17**. The ledger must name those two extra terminal actions or reconcile
   them with a specifically identified mutually exclusive allowance. Successful
   calls need no extra failure payload copy. An error aborts writer/admission,
   so a once-only additional terminal allowance is a source-derived option.

`findings.json` gives arithmetic repair directions with each term named. They
are not a replacement accepted packet. They leave the missing exact checked
emission evaluator and full caller/storage/finalizer closure unresolved.

## Independently corroborated structure

The shape calculation uses **nine** actual conversions, 19 checked additions,
nine checked multiplications and caps yielding Emax69,765,152 and Bmax17,033.
Its itemized501 expansion reconciles. The proof/count getter chain55 for planning
and the source-sensitive copy leaves usage65/failure151/stop152/admission153
reconcile. Fixed pairing has15/25 ticket calls without/with WASI,18/28 through
preflight, and21/31 including the repeated commit preflight. The arrays have
three cache buffers, four WASI buffers, six total categories and two capacity
pairs. No pre-payment payload or cache-content scan appears in these helpers.

The writer has no terminal cursor-None call after its final block. Its positive
write acknowledgement precedes the post-write stop check. Every attempted
block clears4096 bytes, and 32 actual attempts per block bound A<=32B and native
requested bytes<=32E. Stop observations are12+5B+2A, native file events A+3,
opaque getters<=2+3B+2A. Error exits prevent retries after encoder failure,
non-Interrupted I/O failure, zero/overreport or attempt32 exhaustion. Finite
controls independently cover positive-short, Interrupted and terminal prefixes,
small/final block geometries, cap refusals and checked u64 overflow.

The producer's local substitution4259+32*122=8163 is arithmetic-correct, subject
to the findings above. Its native32E is a separate mandatory additive contract;
the per-block clear does not fund it. The once-only transfer initializer4096 is
separate. Neither native-call counts nor this convention bounds syscall latency,
CPU, OS work, allocation, RSS or interruption inside an indivisible operation.

The accepted encoder-only interface remains F14224+26B+68I+39D+139W+Q, with
opaque getter3 already charged by writer terms. The frozen composer's encoder
behavior was independently recovered byte-for-byte against its original
57,293-byte source by removing exactly its frozen measurement seam. No optional
getter charge was duplicated. The encoder acceptance is not writer acceptance.

Repeated attachments and outer getter observations need actual caller counts:
outer16 per attachment call and getter3 per call, with inner45 at most once.
Consuming construct/finish/retire are one-shot. The new wrapper formulas expose
the original selected constructor, construction/header/row work, adoption,
prepare/construct/complete/fail/refund, end-construction, drop-proof, cache/tail,
WASI cleanup and final finish bodies as 14 named inherited dependencies. Those
bodies are bound, but their dynamic cost and F1 lifetime closure are not newly
proved here. Their cost cannot be replaced with zero or an arbitrary fixed sum.

The original frozen `proposed_emission_work_v1` still returns WorkAuditPending;
no admitted writer is reachable through this original proposal. The source's
old planning16384 is not selected by this review. The root-reported raw-owner
selected-constructor bypass belongs to the original composition's separate
authority review; root's active correction folder was neither read nor edited.
A later correction must have its own explicit source delta and review.

## Execution and limits

Run `python3 verification/swift-guarded-snapshot-writer-work-independent/candidate-review/review.py --verify`.
The initial run writes only this review folder; verification compares deterministic
outputs. `results.json` records exact count, Python version and check digest.
`commands.json` records commands, outputs, source reference and restrictions.
The packet seal freezes the compact review artifacts; all predecessor and
producer files remain untouched.

Native/device/simulator/emulator/UI/computer-use/capture, global process
inventories, hosted catalog-inspector/authority-driver/rejected WorkerV2 or broad
hosted harness, and stopped Android experiments were not used. No commits,
pushes, operational selection, storage floor, OTA release, FieldLog dogfood,
store/customer qualification or GA verification are performed or implied.
