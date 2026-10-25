# Independent finite Rust ordered diagnostic review

The frozen producer packet supports **provisional finite feasibility only**.
Complete Rust diagnostic acceptance is withheld. This review reproduces the
finite source and host results, adds ten independent Rust methods, and proves
three malformed CAP inputs can receive a false `truncated-prefix` sidecar.
The full target, live integration and complete bounded analyzer remain unselected.

The reviewed seal is
`c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf`:
186 members, 20,248,850 bytes. Both complete 132-file archives match their
manifests. Exactly four copied files differ, with unchanged Cargo manifest/lock;
actual reverse application restores every pristine hash. The live 132-file VM
closure remains byte-identical. Every retained producer command-output binding
was checked. The review does not mutate or reseal that packet.

## Reproduced evidence

| Scope | Observed result |
| --- | --- |
| Fresh pristine Swift private suite | 340 passed |
| Fresh frozen candidate Swift suite | 356 passed, including the producer's 16 finite methods |
| Fresh pristine/candidate generic private cache | Five each; complete stdout bytes match |
| Fresh pristine/candidate generic integrations | Nine plus one each; only the allocation suite elapsed footer differs, 0.00s versus 0.01s |
| Standalone frozen writer plus new adversity | 13 passed: eight producer and five independent methods |
| New actual-hook controls in an owned candidate copy | Five passed |
| Controlled custody classifications | One valid CAP input and three malformed inputs all returned `truncated-prefix`, failure zero |

These scopes overlap; they must not be added as unique test counts. Rust and
Cargo are the explicitly selected absolute 1.99.0 tools, offline release
compilation, one build job and one test thread. Exact argv, environment overrides,
tool hashes/versions, revision, source closure, raw output and results are under
[the review commands](../verification/swift-ordered-retention-diagnostic-rust-review/commands).
Original fixture files and exact test binaries are retained in bounded archives.

The independent writer methods cover overreported write lengths, attempt-counter
overflow before a write, 32 short writes without completion, code and release
sentinels, closed header/flag ranges, exact cap framing, work-regression freeze,
and footer IO. The footer returned by `finish` precedes any failure during its
own write; the actual writer flags and post-footer attempt count must stay bound
in the outer receipt. No `File::drop` close Result or durability is inferred.

The five independent hook methods exercise publication cancellation with
observation off/on, stale release failure, retained in-flight End while the real
RefCell is mutably borrowed, isolated wrong-thread sticky invalidity, and an
unknown source code with equality of the complete original failure object.
Publication failure preserves the original result/ledgers, records BuildReady
and no PinPublished/Release. Failed stale release returns `stale_pin`, preserves
cache usage and stores no success record; its unselected source code correctly
invalidates telemetry with CODE. End under the retained count writes no footer,
does not borrow the writer, and later actual callback entry refuses without
changing bytes or flags. A wrong-thread fault alone prevents a later owner from
resuming records. These add bounded review evidence; they do not complete all
publication, release, eviction-refund or failure-state qualification.

## Findings blocking complete acceptance

1. **CAP custody status does not validate its claimed prefix.** In
   `capture_finite.py`, the decision `flags == 1` alone assigns
   `truncated-prefix` and failure zero. Three separate 1,280-byte owned inputs
   corrupt header version, first record sequence, and footer stored count.
   Actual descriptor/path metadata and copy hashes remain internally consistent,
   and each still receives that successful classification. These are deliberately
   malformed untrusted-input fixtures, not claimed Rust-produced executions.
   [The exact cases](../verification/swift-ordered-retention-diagnostic-rust-review/custody-adversity.json)
   establish a concrete false-valid path. Keep all unvalidated streams invalid
   until the selected framing/prefix checks exist; a full analyzer remains a
   separate deliverable.
2. **The Rust simultaneous ceiling is not completely established.** The three
   reported arithmetic totals reproduce: callback 12,282, footer 13,394 and
   retirement 15,578 against 16,384; the all-phase union is 19,554. Source control
   flow supports callback/End/retirement non-overlap for the exact synchronous
   owner. The complete original pin/release/failure/usage/WASI owners are charged,
   and the footer/receipt survive into retirement accounting. However the
   synthetic inventory does not separately reconcile Writer construction,
   header returns, Begin/TLS installation, or exceptional guard Drop against
   every live argument/return/borrow/copy. This review therefore does not endorse
   an exhaustive ceiling or claim a demonstrated over-ceiling allocation.
   Compiler copies, physical stack, TLS runtime and OS internals remain unqualified.
3. **The Python named inventory undercounts a retained owner.** An independent
   trace of the finite capture frame observes `reader`, `copy`, `verify` and
   `framed` FileIO objects together at line 63. Three are closed but still owned
   locals; the fourth is open. Actual named FileIO bytes are 256 versus the
   charged 192, an omitted 64 bytes. Correcting just this item yields
   115,803/131,072, so it does not demonstrate a ceiling violation. It does
   demonstrate incomplete reconciliation. This does not break the two live
   copy-descriptor bound. See [the owner trace](../verification/swift-ordered-retention-diagnostic-rust-review/custody-inventory.json).
4. **The producer's declared scope gaps remain gates.** Full field/sentinel and
   state replay, collision/immutable-body/time/tie/victim/work validation,
   complete source-code coverage, real selection/header/binary/harness/target
   binding, actual EvictTaken followed by fallible drop/refund error, and the
   complete custody read/write/error/drift protocol are not established by this
   packet. General concurrent INIT/finalization is explicitly outside its exact
   finite synchronous source closure. The new review controls cannot silently
   close those declared gaps.

## Supported source guarantees

The callbacks are test-only, add no product control/cache/meter field, introduce
no product reservation and change no policy or production limit. The copied
scalar accessor reads existing work/instruction counters without a clock or
WASI snapshot. The pin wrapper observes a borrowed failure then returns the
same original Result. Release observation occurs only after original successful
checks and mutations. Final consuming ledger values come from the original
control, and do not invent per-slot drain events or erase retained replay pins.

For the exact finite owner, entry registers the combined mode/count before TLS,
flags or writer access; normal callback transitions use at most four atomics,
Begin eight and End four, without a retry loop. End closes admission before
count/flag observation and returns before any writer access when count is
nonzero. The non-Send guard binds its lifetime coordinate. Refused closed entry
touches only the combined gate, never flags/TLS/writer. Wrong-thread/borrow faults
latch outside RefCell and a later owner propagates that latch before push. The
bounded count premise remains the selected synchronous owner and joined negative
fixtures; it is not unrestricted runtime readiness. The code table is exactly
24 static strings totaling 502 bytes, and unknown codes preserve the original
failure while invalidating supplementary telemetry.

## Failures, provenance and cleanup

The first pristine review run finished 339/340 because this review runner omitted
the toolchain directory from PATH for an existing test's nested `rustc` command.
The corrected explicit PATH reran the identical 132-file pristine source and
passed 340. The first custody preparation selected multiple same-named archived
lifetimes; an exact lifetime selector fixed it before any copy was created.
Both failed attempts and executed helper versions are retained. A preflight read
used the nonexistent `capture.py` name before reading `capture_finite.py`.

Python's initial SourceFileLoader import created one unsealed producer bytecode
cache. Its exact file/directory ownership was recorded and immediately removed;
sealed producer bytes were never changed. Subsequent helper loading uses
compile/exec without bytecode writes. The exception and cleanup are recorded in
[the import-cache receipt](../verification/swift-ordered-retention-diagnostic-rust-review/import-cache-cleanup.json).

Every owned child completed and was reaped. Exact owned scratch directory
device/inode identities were checked before removal, including failed-attempt
scratch. The [cleanup receipt](../verification/swift-ordered-retention-diagnostic-rust-review/cleanup.json)
confirms no owned scratch remains and live132 is unchanged. No process discovery,
native/simulator/emulator/device execution, UI automation, capture, full target,
live integration, commit or push was performed by this reviewer. No native,
provider, customer, FieldLog, operational or GA gate is promoted.
