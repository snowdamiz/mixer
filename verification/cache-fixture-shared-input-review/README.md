# Independent review of shared context-fixture inputs

Decision: the exact candidate source is acceptable for one root-selected bounded
remote full-fixture diagnostic. There are no blocking source findings. This is
source acceptance only; there is no compiled-pass or speedup claim.

Reviewed candidate SHA-256:
`f7d62c01e251642677e22f7595af9683f9c451f1db43683be5d2ef86fedba141`.
Original SHA-256:
`7c9c3006e1e7fd6a927fc7c3ca472c33abe3084f50a1f5aea0d31c6d9d75c411`.
The frozen pack remains byte-exact at manifest SHA-256
`d1caf2069e17ac1beff6707d6e084ea49d18382bc959d73d5184ec49cb7886b9`
and tree SHA-256
`ab2d0a6ef1c0df25f9624fc4b7d72cb0007df749fd1ed88bf43f243336eeedb2`.

The historical timeout remains a failed observation. Root supplied later
unchanged passes, including 52.410318 seconds on E9 and passes on 5ef/295;
those were not independently refreshed in this source-only lane. This proposal
does not establish a current CI failure or a product regression.

## Source findings

- Removing only the new helpers and restoring the context method reproduces the
  original complete source byte for byte. The general `run()` and copied
  result/report assertions are byte-exact. All 1,003 ordered context identities
  match an independently encoded context baseline and the saved inventory.
- Shared stream/profile paths are created once as separate regular files before
  any case, made read-only, and checked before and after the loop. Fresh
  `File::open` calls give each case fresh file descriptions/cursors; no
  `try_clone` or reused reader carries a prior offset. Context/report are fresh
  distinct files. The analyzer's pairwise device/inode test applies within each
  invocation, so reusing the shared input inodes across separate calls does not
  collide. Read-only permission bits are admitted by the analyzer and stay
  stable throughout each invocation.
- Every invocation still enters the unchanged analyzer through
  `analyze_fixture`; each constructs a new 8 MiB arena with all 1,048,576 paid
  initialization extensions. There is no cached analyzer, arena, report, budget,
  capability or accepted result. Existing alias and output freshness safeguards
  are unchanged. Read-only mode is additional defense, not adversarial custody.
- Result/report assertions precede handle closure and case removal. Panics leave
  the active case and shared files under owned scratch. The actual existing
  runner's recursive cleanup retained all four simulated failed-case/shared
  files byte for byte before deleting owned scratch. Incorrect ownership markers
  and an active-custody sentinel prevented deletion without probing any process.
  Successful cases remove only their own directory; shared files survive until
  the final count and content checks succeed. Unix unlink of read-only regular
  files is permitted through the owned writable directory; compiled Darwin
  behavior remains for the diagnostic to verify.
- `completed` advances once after `run_context_opened` returns, including case
  cleanup, and the final exact count is 1,003. New standard-library types,
  immutable vector borrows, mutable file-reference array, `Duration` accumulation
  and copied `Instant` use appear type-correct for the declared Rust editions and
  toolchains, pending real compilation.

Two timing interpretation limits require no source change. `prepare_ms` measures
case directory/context-file creation and handle opening; caller context cloning,
baseline/shared setup and content checks are included only in `elapsed_ms`.
The `completed=1003` progress line also precedes final shared validation/removal.
Accept completion from the full command's success and postflight receipt, never
from that progress line alone. Saved phase totals should include an explicit
unattributed elapsed remainder rather than pretending they sum to total time.

Avoided traffic is exactly 2,568,193,536 profile clone bytes and 2,565,633,024
profile file-write bytes. The candidate additionally reads the shared profile
twice for content checks and retains the large arena initialization cost. These
byte counts are not a performance estimate.

## Executed evidence and boundary

Command: `python3 -B verification/cache-fixture-shared-input-review/review.py`.
The 16 grouped checks passed under Python 3.14.8 on Darwin, with zero denied
operation attempts and complete removal of this lane's disposable file-control
scratch. The script denies child/socket operations and patches signal, wait,
process-control and sleep entries. It never runs the compiler, Rust product,
fixture executable, Git, UI, native runtime, capture, held probes or dispatch.
It imports the frozen Python runner only to execute `verify_pack`, `identity`
and `cleanup` with synthetic owned data and no child state. The small file
controls exercise real Python file operations; they are not Rust runtime proof.

The report binds all 101 source/evidence read-set files before and after the
checks, including every frozen pack member, both Rust source versions, source
proposal evidence, current runner/control code and workflow. Its read-set digest
is `1f027a9c2a2c3a779fbd44f9cbb10f90c171a798835b2fe3bbd46f24d16389b7`.
No current Git revision was probed; the exact read-set hashes bind this review.
The sibling seal covers this review's own files. No canonical/global file was
edited and no delivery campaign was selected by this lane.

`integration-map.json` is the concrete minimal integration map. Root can select
and implement it without another source-review cycle by default. Required
remaining evidence is real compiler/focused-runner/full-fixture execution on the
declared compiler under unchanged limits, with output, ownership and cleanup
receipts. Native/phone/capture checks stay paused or pending; this host fixture
does not carry release or GA authority.
