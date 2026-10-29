# Focused hosted admission custody correction

This sibling corrects the process custody source contract before any hosted
admission was run. It is source/data preparation only. The original packet at
`verification/android-view-api-boundary-host-admission/` remains frozen at seal
`67216246e69f0fed1c3861a9ff6134f944924544f62d8f1e0704edfc90e60445`
(17 sealed members, plus the seal). Its independent source/data review passed
110 controls, but that preparation did not detect the subsequently found custody
bug. No previous runtime admission is inherited. `baseline.json` preserves all
original member hashes; `changes.json` records exact correction identities.

The original helper used `Popen.wait()` as direct-reap evidence. CPython can
return a cached returncode or synthesize zero after ECHILD without a successful
kernel wait. It also attempted a final group signal after nonreaping wait identity
loss. The corrected helper never treats a Popen result as kernel evidence.

Normal acceptance requires this order:

1. Observe the exact direct child terminal status with `waitid(WNOWAIT)` while
   retaining the child unreaped and drain stdout and stderr independently to EOF.
2. Permanently retire signal authority in memory before persisting that fact.
3. Call raw `os.waitpid(exact_pid, WNOHANG)` and require the exact returned PID,
   a canonical terminal raw status, and equality with the unreaped observation.
4. Consume at most one post-reap `killpg(pgid, 0)` absence-only observation.
   ESRCH means absent at that instant. Presence, EPERM or unknown errors hold
   without further numeric signals, waits, probes or child admission.

Every permitted cleanup signal first repeats the nonreaping identity observation.
ECHILD, mismatched identity/status or unknown wait ownership retires signal
authority and latches the session hold before any evidence write. There is no
subsequent numeric signal/probe or fabricated reap. The original finite wall,
cleanup, final-observation and output limits remain unchanged. Exceptional cleanup
with still-proven unreaped authority can signal within those bounds; missing EOF
or any earlier rejection remains failed, even if a direct reap later succeeds.

`NonReapingPopen` preserves the reviewed new-session/exec setup. Its destructor is
inert, its references remain retained even after constructor failure, and public
and private reap/signal/context methods refuse. The empty Popen cleanup list is
checked before construction. CPython may directly wait during an exec/setup
constructor failure; that path grants no signal authority, never supplies a
successful direct-reap receipt and permanently holds the collector.

The selected standalone Linux x64 Python process must already have default
SIGCHLD disposition, no native SA_NOCLDWAIT, only its Python main thread, and an
empty Popen cleanup list. A read-only `sigaction(SIGCHLD, NULL, &current)` checks
the Linux/glibc x86_64 152-byte ABI, in addition to Python's disposition view.
The pointer/long/int sizes, complete field offsets and total size must match
before the query. The copied `linux-signal-abi-source-receipt.json` binds the
glibc2.39 Linux source layout; its `localRaw` entries refer to the original
`verification/android-view-api-linux-signal-abi-correction/` packet, and raw
headers were not copied here. That receipt preserves and rejects an earlier
generic-header derivation. Installed Ubuntu libc bytes are not independently
proven. Unknown ABI/query/handler/thread/reaper state refuses before spawn. No process
disposition is changed. The exact Ubuntu provider, Python/bootstrap/stdlib,
libc ABI/dynamic loader and absence of an external competing reaper remain
explicit infrastructure assumptions. The bootstrap uses `-I -B -S`; an already
running collector cannot independently prove its bootstrap or hermetic isolation.

The session holds in memory before fallible JSON or stream persistence. The hold
survives fresh custody-module imports in the same interpreter; collector entry is
once-only across fresh module imports as well. Before a tool child, the collector
exclusively creates, flushes and fsyncs a nonce reservation, then fsyncs its parent
in the selected `RUNNER_TEMP`. Any existing or partial reservation refuses retry,
including a fresh output path or process on that same filesystem. Reservations
are retained and uploaded. This is not cross-provider nonce enforcement; root's
one-shot selection/delivery policy still controls fresh provider runs. Host loss
may prevent custody settlement or artifact upload and remains held.

The six fixed command argv, emitted-map D8 prefix, seven-child count, allowlisted
environment construction and all numeric tool bounds are unchanged. The product
115-member closure, product16 tree, source-manifest148, inspector, JDK runtime74,
SDK37 and D8 inputs are byte-identical to the original packet. D8's final class
filenames still require actual inspected SDK output during the separately
selected future run. No compiler, JVM, SDK/D8, product, native/UI/capture/phone,
Git/gh/network or dispatch action ran in this correction lane.

`test_preparation.py` denies real process/session/group/signal/timer/wait/socket
and ctypes load/query surfaces before either subject import, including available
captured subprocess wait aliases. All process, clock, stream, SIGCHLD and native
query behavior is synthetic. Source/JSON/AST and ordinary filesystem checks are
real. Its controls cover the original focused closure/argv/limits and the custody
negative cases, persistence failures, both-EOF ordering, no later access/child,
implicit Popen paths, module reimports and nonce reservations. Every attempt is
retained in ignored `local/`; `preparation-controls.json` records the final source
identities and passed controls. These controls provide no runtime or native pass.

All 265 producer checks passed. The final geometry-corrected sources passed
20 independent paired grouped controls and 43 native prerequisite/Popen checks. Independent sources and receipts are bound in
`independent-controls.json`; these counts do not imply runtime acceptance.

Root owns installed workflow naming/installation, immutable revision, selection,
Git delivery and any future dispatch. The draft remains outside
`.github/workflows`. This sibling grants no execution, publication or credential
authority. Existing hosted/native/process/custody holds remain in force. Escaped
descendant absence, provider disposal, native parity, canonical source pairing,
full rendering below API36, physical phones, OTA/release and GA remain unproved.
