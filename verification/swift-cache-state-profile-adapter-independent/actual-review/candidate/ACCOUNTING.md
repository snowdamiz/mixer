# Exact-source accounting and lifetime argument

`accounting.py` binds this inventory to the final adapter SHA and complete copied
VM tree. `accounting.json` records every measured complete Rust type, caller tuple,
helper/error transfer, source function span and conservative logical place count.
Debug and optimized measurements must agree. This is an independently reviewable
source-level bound; it is not a measured machine stack frame, RSS, CPU instruction
count, standard-library implementation bound or inherited fixture G debit.

The complete row is 32 bytes, observation 64 and error 32; the complete row Result
is 40 and writer Result 72. The standalone row caller tuple is 88 bytes and writer
caller tuple 152. Complete admission Result is 40; the complete metadata Result is
152, its owned Metadata144; each write/position Result16. The actual snapshot
object is664 and a descriptor32. Padding/alignment and hidden Result discriminants
are included through compiler measurements, rather than payload-only accounting.
The JSON deliberately adds all mutually exclusive phases, all lexical errors and
conversion Results, and conservative scalar padding. It even sums the external
row and writer caller places although no writer recursively calls its external
caller. This whole sum bounds each actual simultaneously-live subset without
reusing a return slot or assigning unused capacity to another owner.

At preflight, the caller owns the snapshot and File; the wrapper borrows them,
checks the snapshot, obtains/drops metadata and position Results, and then enters
the writer. The block does not exist during File admission. No ownership moves
out of the caller. During row derivation, the writer block/counters/iterators,
row Result destination and private callback remain live. The row helper borrows
the sealed owner, checks observations, calls `execution_function(absolute)` and
borrows exactly that descriptor/body. Its nested admission's observations return
before the helper's own observations are made. The descriptor/body cannot escape
in any scalar row or error. During encoding, descriptor/body borrows have ended;
only the32-byte row and one output block exist. LE temporaries are at most8 bytes
at once; all five are summed anyway. During a write, row-helper frames have ended;
the borrowed block remainder, callback File borrow and complete I/O Result are
live. During finish, the same block remains reserved while scalar observation
conversions/Results are produced. All failure paths return one scalar error,
retain caller File ownership and partial bytes, then drop block/closure/borrows.
No error retains a body, File, snapshot, heap collection or text.

The snapshot's retained source and metadata are separately owned and remain
charged under the unchanged64MiB/16MiB limits. Validation has its own1MiB scratch,
512,000,000 work and120,000ms caps. Those costs are not swallowed by this adapter's
logical-place sum. For the observed last admitted position the source is321,731
bytes, metadata reservation961,544 and validation total peak1,284,331; the source
input visible bytes and retained source are distinct observations. The caller's
arbitrary unrelated memory and allocator/OS overhead are not covered. This
host-only prerequisite adds no engine budget reservation/debit and changes no
existing limit. Later integration must assign actual charges; this packet does
not borrow the fixture's29,344 union or7,048 G1..G7 totals.

Every explicit product-source loop is closed:625 outer blocks,128 row derivations
per block, and at most32 write calls per block. `step_by`/range induction is
bounded by the constants, and local*32 plus32 is at most4096. The widened helper
error coordinate fits u64 even for MAX32. Imports+defined, body offset+length and
all usize-to-u64 returns use checked operations. `bytes`, `done`, `calls` and
`attempts` use ordinary increments whose induction bounds are2,560,000,4096,32
and20,000 respectively; returned overreports never advance them. The fixed
policy string comparison is at most27 bytes. The shared source lookup uses
checked index subtraction, one metadata index and one retained-source span;
it scans/copies no body. Observation copies are fixed136 bytes. Encode contains
five fixed conversions/copies totaling32 wire bytes; there is no row/profile Vec.

The JSON lists conservative action allowances for the complete control/transfer
source, including all error exits and nested admission, with no uncategorized
loop. Its units are explicit source actions, not executable VM instructions.
Maximum cumulative requested I/O slices are81,920,000 bytes; successful
acknowledgements total exactly2,560,000. Interrupted calls can repeat a slice and
consume attempts only. At call32, success requires block completion; incomplete
or Interrupted returns exhaustion, while zero/error/overreport retain their
specific failure. Every error offset is either preflight0, the widened row wire
coordinate, or the acknowledged write cursor. `with_progress` adds the writer's
successful byte/attempt counts without changing a row error's coordinate.

Metadata/position queries each occur once; writes are bounded as above. There is
no finish syscall, fsync, reopen, truncate, alternate output, digest or
custody operation. A host syscall may block; source bounds are not a wall-time
promise. Every test child has its unchanged60-second process-group deadline.
The File assumption is regular, empty, initial offset0 and caller-quiescent
including alias/OFD seeks. A short/faulting writer can physically change bytes
without returning a count; no error claims rollback or knowledge of those bytes.

Safe real sealed owners cannot reach inconsistent metadata/policy/descriptor or
64-bit narrowing failures under current limits. They remain defensive branches
with fixed codes, source-reviewed here; no forged owner/constructor is introduced
to claim runtime coverage. Likewise metadata/position syscall failure cannot be
injected safely into a valid File without adding a new authority seam. Actual
nonregular/nonempty/nonzero-position File checks run. Private callback tests
exercise every write category and call31/32/33 boundary, with actual partial File
bytes independently encoded and retained. Zero-allocation observations exclude
validation, test encoding, test printing and bridge setup.
