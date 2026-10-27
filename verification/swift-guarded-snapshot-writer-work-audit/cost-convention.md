# Writer/control logical action proposal

This packet extends the frozen encoder proposal's `cost-convention.md`, whose
original 30-member seal remains unchanged. Root subsequently accepted its
corrected **encoder-only** interface at
`verification/swift-semantic-adapter-root-review/guarded-snapshot-encoder-work-host-acceptance.json`
(SHA256 `757345abe9013a4d5d880738c794e8a9783061fb733f4de24f432698861e9351`).
That acceptance does not accept this writer/control proposal or select a full debit.

One fetch/store/scalar operation/decision is one action. A repository function
entry and return cost two. A constant-depth named place is one fetch; literal and
bound local operands are free. A checked operation includes its overflow result,
but `?` adds inspect and extract/propagate (two). `map_err` costs three without
the selected closure body. `ok_or` costs inspect and output carrier (two), with
its eager error construction counted separately. A `filter` row costs six:
Option inspection, borrowed predicate fetch, comparison, branch, output Option,
and predicate call boundary allowance. A fixed indexed access includes a bounds
comparison plus the scalar fetch/store. Arrays initialize each explicit slot;
fixed byte fills cost every byte. For loops have two setup/termination actions;
each iteration advances and binds (two), or advances and binds a tuple (three).
An outer `loop` has two setup/termination actions and two per iteration.

We sum the scalar work of alternative success/error arms where convenient.
This is an upper sum of written branches, not an unexplained multiplier. Error
helper invocation and large diagnostic copies are charged separately once per
invocation because the first terminal error returns immediately. The ledger's
named rows expose their component sums and expanded helper dependencies.

An explicit aggregate Copy from a borrowed source is a fetch/store per leaf
slot. A scalar enum is one slot; a payload enum is its tag plus the largest
payload; Option adds a tag. A reference, including `&'static str`, is one logical
slot under the inherited reference convention. This is source-level work,
not a physical byte, ABI-width or compiler memcpy count. Moving owned payloads
through Result/Option propagation does not imply another deep copy.

Copy expansions are:

| Type | Leaf slots | Derivation |
| --- | ---: | --- |
| SwiftReservations | 18 | eight current/peak pairs plus live/peak tickets |
| SwiftLiveUsage | 12 | six current/peak pairs |
| SwiftValidationUsage | 10 | ten scalar fields |
| WasiUsage | 13 | six counters plus seven reservation fields |
| SwiftRunUsage | 65 | 18+12+5 counters+2 cleanup Option+2 times+1 origin+1 overshoot+10 validation+14 optional WASI |
| SwiftRunFailure | 151 | 20 diagnostic slots+65 at_failure+66 optional after_cleanup |
| SnapshotStopV1 | 152 | tag plus largest Existing payload151 |
| SnapshotAdmissionErrorV1 | 153 | tag plus largest Stop payload152 |

Writer late-tail628 = one Existing copy302 + at most one post_stop copy304
+ error helper16 + cause tag1 + Err carrier1 + lazy closure entry/return2
+ two selected Option argument constructors2.
The error helper16 includes entry/return2, four scalar/ownership slots and the
five progress field fetch/store pairs10. A successful stop does not copy a full
failure. Only one error callback can be selected. A post-write stop retains
already acknowledged bytes; checked arithmetic failure may copy post_stop into
its selected error closure. Admission instead has its own late-copy tail608:
Existing302 and one AdmissionError duplication306 into both refused access and
refusal storage. A later borrowed `storage.refusal.expect` at branch export can
copy another306; it is a caller term, not hidden in writer628.

Each native call is one **logical call event** at its source occurrence.
Metadata/seek/write implementations, OS time, allocation inside std, atomic and
clock implementation work are not expanded or bounded by this convention.
Cancellation atomic load and `Instant::now` are separately named logical events.
There are at most A+3 file-call events (writes, two metadata calls, one position
call). Native calls remain cooperative indivisible operations; these counts do
not establish wall time or a deadline interrupt inside the syscall.

The original repeated-transfer contract also requires **32E additive requested
native bytes in any complete paid emission formula**. These bytes are distinct
from source logical actions, the encoder's copied Q<=E, the writer's 4096B clear,
and the admitted transfer buffer's one-time4096 initialization. The source
logical formula1214+8163B alone must never be selected as complete emission work.
The additional32E is a work contract envelope, not a claim that std copies every
requested byte in-process or that an OS write consumes bounded CPU time.

All coefficients here remain proposals until separate independent source review.
No complete planning/work evaluator, caller, storage or finalizer acceptance is
implied by finite Python model checks.
