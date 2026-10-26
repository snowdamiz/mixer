# Failed seeded first-pass source proposal

This concrete proposal stops on a new G2 obstruction. A valid 64-resident,
64-live-pin AcquireBegin path has a necessary subtrace of **29,248 scalar
operations plus832 complete payload copies**: `ceil(29248/16)+832 =2660`,
**100 groups over the unchanged G2 cap2560**. This is a conservative lower
bound. The many uncounted loop, validity, total, mask, view, tail and return
operations can only increase the complete source cost.

The source implements the proposed finite lead. Actual G2 occupied/pin probes
derive one eligibility u64; all64 tail slots remain timestamp-initialized.
The mask is stored at original Candidate bytes640..648, explicitly proposed
unused scratch within the existing first1536 bytes. Initial A/B index seeds
are removed. Width1 reads the mask, materializes all64 one-hot constants in
source, loads actual complete u64 timestamps, and writes32 two-slot blocks to
original B1024. Each pair comparison yields both output slots. Five later
passes remain byte-identical to the prior thin-array, cached-head, fully
source-written design. The final output remains A512. There is no macro,
optimizer elision, new helper, unsafe conversion, timestamp sentinel, hidden
eligibility producer, or new capacity. This layout amendment is **unselected**.

The all-eligible bit-reversal merge witness counts G3 **2443 groups** and G4
**543 groups**. These are finite necessary subtraces, not full upper ledgers
or passes. Mask loading, complete view/tuple/Option construction, cursor
construction, block continuations and callee unit/return remain positive
unaccounted merge work. A successful initial merge floor cannot overcome the
separate G2 obstruction. Therefore the complete G2–G5 upper/role ledger was
not built and no all-group acceptance is claimed. G5 remains unqualified.

The G2 witness uses64 occupied residents with distinct functions, bytes1 and
pins1, plus64 live pin entries back to those residents, nonces1..64, next
nonce65 and idle envelope state. AcquireBegin1 may request an undefined body
and does not require a free token. Such a state is reached by64 successful
build/publications held pinned; capacity128 and entry1 permit that prefix.
Every checked byte addition succeeds; every live-pin backlink guard succeeds.
`w[1] ==12` is false, so its RHS is correctly absent. This G2 path is separate
from the all-eligible merge witness; no incompatible per-path state is joined.

The exact selected subtrace per slot counts:

| Actual source component | Scalar operations | Complete copies |
| --- | ---: | ---: |
| Seven resident array8 loads | 249 | 7x8 |
| Timestamp array assignment | 26 | 1x8 |
| Successful checked addition and Option pattern | 13 | 1x16 |
| Four live-pin/backlink array8 loads | 142 | 4x8 |
| Actual short-circuited release-kind condition | 27 | 0 |
| Total, each of64 slots/pins | 457 | 13 |

Every array Index retains fixed/fat receiver transfers, bounds operands,
width scaling, received reference/dereference/result edges and all source
index expressions. Fat slice Index21 differs from selected fixed Index20
only by its actual received length transfer. LE input arrays move complete8
bytes. The returned timestamp array moves once directly to its indexed
destination: no invented second temporary inflates the obstruction. The
checked addition moves its complete Option16 and retains its tag/payload,
overflow, call, pattern and result work. The sole selected `w[1]` scalar load
retains Index20 and width8 scaling. Neither a full array/Option nor its
inactive bytes are replaced by a scalar shortcut.

`component-templates.json` and `finite-subtrace-ledger.json.gz` name every
counted primitive/operand/copy once and partition scalar groups at16 and copy
groups at128 bytes or less. Positive omissions are explicit. The independent
verifier imports no producer code and separately checks source custody,
arithmetic, coverage and finite mathematical merges including all-ineligible,
short tails, equal timestamps, actual u64::MAX keys and stable lower-slot
ties. These mathematical checks do not execute the proposed Rust or establish
fixture entry behavior, compiler layouts, source upper bounds or lifetimes.

The whole proposed source/diff binds to frozen C3
`0ab577c36f9836539181ba5156bdfbc7764ea065266e68d94b431da5fdb47ea8` and the exact
18-member/2,799,286-byte prior packet whose seal is
`7617d00155a50807ecdd92a4841ab51225fee25a4f116f98c34341eaba3a30d6`.
The G6 event staging, exact merge caller and headroom boundary, post-prefix
suffix, row/staging1536+, scalars1688+ and cleanup remain unchanged. Selected
G6 retains its four caller-only operations; G3/G4 callee work cannot be spent
there. G2=2560, G3=2568, G4=768, G5=640, semantic7680, Candidate2048,
roleunion29344, control addition1280 and wire addition256 are unchanged.

No existing control-lifetime proposal authorizes the changed owners. The
unselected local role inventory lists exact proposed owners but makes no
complete29344 or helper fit claim. Full source/received/caller lifetime work,
fresh layouts, all-group qualification, compiler/native/device tests,
published-package FieldLog, signing/store/operations and GA remain pending.
The first-pass test-only atomic counters have not been adapted or qualified;
their production-independent accounting is outside this failed source gate.

Only this new directory was written. No product implementation, frozen input,
root metadata, Git, hosted read/import/execution, compiler, Rust runtime,
native instance, UI, capture, process inventory, commit, push or publication
was performed. No runtime/build directory was created or needs cleanup.
No other project's processes or data were inspected or modified. Root owns
selection and independent review; this finite failed proposal stops here.
