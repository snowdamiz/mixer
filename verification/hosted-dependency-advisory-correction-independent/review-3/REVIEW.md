# Focused independent resolution-v4 source review

Recommend root's exact single five-command resolution-v4 operation, using plan
SHA256 `150cee180b4cfe30a7dc293b9f041308cd0c06ec4cb69b65a200f77a1bf300c4`
and unchanged 40/46/52/55-second stages. No blocking source finding remains.
This supersedes review-2's runtime readiness recommendation; its sealed evidence
and every original/v2/v3 packet remain immutable and unexecuted.

The change responds to root's report of a separate failed Swift operation. That
operation did not identify its precise failing syscall. This review establishes
neither an EPERM cause nor successful runtime behavior of the replacement.

Normal completion now takes WNOWAIT's retained exit witness directly to
`Popen.wait(timeout=0)`, without TERM/KILL, then only observes group absence.
Already-reaped cleanup also observes only. A group that remains or cannot be
observed makes closure uncertain and preserves scratch. No new command starts
until the prior group is recorded closed.

Forced cleanup requires confirmed child custody, an unreaped child last observed
running, and controller cancellation/timeout. A fresh WNOWAIT check immediately
precedes each TERM/KILL; a witnessed exit switches to the no-signal reap path.
There remains an unavoidable race between observation and a signal. EPERM now
permanently latches cleanup refusal, retains the API/errno evidence and forbids
later cleanup retries or alternate kill actions. It is never converted to group
absence, and unknown group closure prevents owned scratch removal and success.
Controller cancellation also covers aborting remaining work after a work error;
the receipt separately records that cause from a handled user signal.

The custody wrapper records process launch, getpgid/getsid, WNOWAIT, wait and
killpg boundaries. Selected process-control arguments are retained, with errno
and symbolic name, normal exit status/code/time, signal history and a last-32-call
ring. Each chained traceback retains at most 8 KiB with explicit truncation;
the existing 1 MiB receipt bound still applies. This is Python/API evidence and
does not assert an otherwise unobserved underlying syscall.

Fresh hashes verify the six-member v4 seal, six v3/five v2/sixteen original
members, both prior independent reviews and all selected packet, canonical,
tool, Hex and advisory pins. Twelve existing function ASTs are unchanged,
including the finite signal cutoff, verified-byte reader, lock parser, output
and disk guards, source verification and owned-tree removal. Five exact command
arrays, private DNS/file inetrc and BEAM home, unchanged shell HOME, TLS/registry
checks, two selected versions and nineteen unchanged-entry requirements remain.

The audit ran only bounded Python file/hash/AST checks, without importing or
executing the controller. No Mix/compiler/native/network/DNS/process probe ran.
The proposed operation remains lock generation only; actual lock-diff and
closure review, product tests, remote CI, HTTP/2 wires, deployment and GA remain
pending.
