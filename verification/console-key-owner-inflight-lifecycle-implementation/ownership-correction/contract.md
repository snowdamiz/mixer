# OpenSSL wrapper custody correction: proposed contract

This is a source-only proposal for root review. It authorizes no implementation
or execution. prepared-3 remains unexecuted. No product or existing test change
is selected beyond the already accepted charlist spelling.

## Evidence and claim boundary

Candidate 2 recorded one completed OpenSSL version call: wrapper PID/PGID 58589,
native PID 58594, retained test VM group 58517. OTP's selected Unix child setup
explicitly establishes a process group/session before exec (source lines
326-332). Root subsequently sampled only recorded PGID 58589 and found it absent;
that later check does not prove the earlier containment assumption.

The correction owns each selected OpenSSL wrapper group explicitly. It does not
equate a System.cmd group with its VM group or claim a whole VM descendant tree.
The trust boundary is the frozen wrapper/interpreter/native tool, selected argv,
explicit environment and exclusive mode-0700 run directory. Same-UID hostile code
forging the protocol or changing process identities is outside this test harness
contract. Nonces bind a run/invocation; hashes bind bytes, not OS process identity.

## Selected protocol

Use a private file spool, avoiding a new service, helper process or dependency.
Every message is capped JSON with exact fields/types; publish by exclusive temp
file, flush/fsync, atomic rename, then directory fsync. A partial/duplicate/
symlink/escaping or mismatched message never authorizes a launch. Each invocation
uses a fresh nonce; retries/replays cannot obtain a second launch grant.

1. **Register before native launch.** The wrapper installs signal/deadline
   handling, validates pinned local configuration, then publishes its run and
   invocation nonce, PID, PGID, SID, wrapper/interpreter/native identities, argv
   and requested deadlines. No OpenSSL Popen, output helper or version probe
   occurs before a valid runner ACK. Accept only the selected OTP group-leader
   shape PGID == wrapper PID > 1; this is independent of the VM group. An
   unexpected group shape is denied, not moved or killed as an arbitrary group.
2. **Retain before ACK.** While its launch latch is open, the runner validates the
   exact message, selected identity/recipe, nonce/hash, time budget and current
   exact PID/PGID/SID. It appends and fsyncs a root-owned custody journal record
   before publishing a launch ACK bound to that request hash, nonce, PID/PGID,
   root plan and absolute deadlines. On any validation/journal error it grants
   nothing. It retains every proven registered group for final cleanup, including
   a valid request declined after the work cutoff. Invalid claimed groups are
   recorded as rejected and never signaled.
3. **Launch once and retain child accounting.** The wrapper accepts only its
   exact ACK while it remains within the ACK/work deadline, rechecks its own
   PID/PGID/SID, then starts the pinned native command without a new session or
   group option. It immediately publishes the exact child PID and observed child
   group, or records rapid exit followed by exact wait. It retains bounded output,
   native exit/signal, deadline and child-wait results. A child group discrepancy
   fails ownership; it is never silently relabeled as VM containment.
4. **Hold the leader through completion.** After exact native wait, the wrapper
   fsyncs completion and remains alive for a hash-bound runner exit grant. The
   runner records completion before allowing the wrapper to return bounded
   stdout and exit. Custody is retained until the exact group is observed absent.
   Once absence is observed, that terminal PGID is never signaled again.

The runner polls registration/completion during stdout reads and every work and
cleanup wait. ACKs close irrevocably at work cutoff or any observed signal/error.
It continues collecting late valid requests for cleanup, without native grants.
No acknowledgement is inferred from a file merely existing: its exact complete
binding and runner journal acceptance are mandatory.

## Bounds and cleanup

Preserve work/cleanup/post/receipt cutoffs 40/46/52/55 seconds and the current
output caps. Select ACK wait at most 1 second; native work at most 5 seconds per
invocation, capped by the runner's work deadline; wrapper child cleanup at most
the shared 46-second cutoff. Use the pinned host's shared monotonic_ns clock.
Success still requires one version plus six fixture calls, two sequential TLS
fixtures and nine methods. There are at most seven native grants; allow at most
16 published requests for bounded rejection/failure evidence, then fail closed.

Wrapper timeout, output overflow, ACK loss or SIGINT/SIGTERM/SIGHUP closes its
local launch path, terminates/kills only its exact native child as needed and
waits it; results survive in completion evidence. Signal handling must not abort
native wait or ownership publication. The runner closes grants, retires its
retained VM groups, ingests pending requests, and TERM/KILL-drains each proven
registered group within its cleanup budget. A group action requires the current
exact registered leader identity/group still valid; no delayed name/PID-only
cleanup is permitted. A lost leader with a still-present group is uncertainty,
not authority to signal a potentially reused group. This local lifecycle guard
is not an atomic OS process-generation handle.

Scratch removal requires retained VM children reaped, every registered group
observed absent, complete custody accounting, no unresolved bootstrap/spawn/wait
uncertainty and no cleanup error. Otherwise preserve scratch, fail and retain
the exact unresolved records. A later absence sample cannot retroactively pass a
failed custody interval. No global inventory, unrelated PID/group action or
fallback recursive process kill is allowed.

## Bootstrap and unavoidable gaps

Interpreter/OTP wrapper startup precedes registration. If startup/import fails or
hangs before publication, no OpenSSL native launch is permitted by this protocol,
but the runner has no proven wrapper group to kill. An interrupted/incomplete
handshake therefore fails with cleanup uncertainty and preserved scratch; do not
claim that the VM group contained it. Frozen bootstrap bytes/environment reduce
this gap; they do not remove it. Likewise process creation, uninterruptible I/O,
runner hard kill and untrappable wrapper death can prevent bounded completion.
Retain the missing/unfinished state instead of advertising unconditional cleanup.
Python's documented process-creation timeout limitation applies.

## Review and future verification

After root contract review, implement only wrapper/runner/evidence plumbing and a
new separately frozen candidate. Retain the charlist correction, nine methods,
zero compiler-warning rule and KOL09 adverse-result policy. Extend exact output
membership and typed custody evidence deliberately; do not suppress OTP reports.
Future bounded controls must cover: no ACK/no native launch; journal failure
before ACK; valid durable ACK/child wait/leader release; signal or timeout while
native work is active; malformed/replayed requests; and prepublication failure
with honest uncertainty/scratch preservation. Those controls and the real host
run require separate root review/release; none runs in this packet.

Sources and exact retained input hashes are in source-bindings.json. Native/UI/
capture/emulators/phones, product/network/provider qualification and GA remain
pending. The separate CI fixture-cleanup lane is outside this contract.
