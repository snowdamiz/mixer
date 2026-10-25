# Apple command finalization observer V1

This is standalone source and host diagnostic tooling. It has not run or selected
a native command and is not integrated into a runtime packet, harness, authority
driver or catalog inspector. It does not diagnose the causal subsystem of the
retained V3 Xcode timeout. Full product scope and native acceptance remain open.

The retained `Commands.run` starts an exact command in the repository working
directory, supplies its explicit environment, uses `start_new_session=True`, and
waits for `Popen.communicate(timeout=600)` for the selected test invocation. The
historical selected suite finished after about 35.5 seconds, but that command did
not return before its 600-second timeout. Its result bundle lacked `Info.plist`.
The failure analysis distinguishes test suite output from process completion;
there is no retained process/EOF/result-finalization timeline proving the cause.

## Public contract

`verification/apple-command-finalization-observer-v1/observer.py` exports:

```python
observe_command(
    argv, *, cwd, env, output_dir, owned_result_root, result_bundle,
    timeout=600, check=True, poll_interval=0.25, post_suite_grace=10,
    max_output_bytes_per_stream=32 * 1024 * 1024, encoding=None,
) -> tuple[int, str, str]
```

The caller supplies the exact already reviewed command, working directory and
environment. The observer does not construct or select Xcode commands, test
methods, destinations, packets, permissions or retries. Import has no native
effect. A future integration must explicitly select the exact invocation and
retain all strict XCTest, bridge, oracle and final acceptance assertions.

The command runs once with the supplied argv, cwd and env, and
`start_new_session=True`. The tuple has the original `Commands.run` shape: exit
code, stripped stdout, stripped stderr. `check=True` raises `AssertionError` for
a nonzero completed command. `check=False` returns that unchanged exit code and
does not suppress observer, decoding, overflow, interruption or timeout failures.

The command completes only when the owned direct child has exited and both
original stdout/stderr pipes have reached EOF. One nonblocking reader consumes
each pipe; there is no competing `communicate` reader. Each stream uses strict
incremental decoding with the same default encoding selection as
`Popen(text=True)` and universal newline normalization, including split UTF-8 and
CRLF. Byte logs retain the original bytes rather than normalized text. Host
controls compare these return values to `subprocess.run(..., text=True)`.

This is deliberately bounded capture: each stream retains at most 32 MiB, with
a smaller caller limit permitted. An overflow raises `OutputLimitExceeded`,
preserves its bounded raw prefix and diagnostics, and cleans the owned group.
It never returns truncated text as a successful result. Invalid encoding and
reader errors likewise fail closed. No environment values are recorded; callers
must keep secrets out of argv and output or add reviewed redaction before any
future integration. This standalone module has no capability or secret input.

## Timeline and completion markers

Each newly created owned output directory contains `stdout.log`, `stderr.log`,
`timeline.jsonl` and `observer.json`. The receipt records exact argv/cwd, Python
encoding, limits, the direct PID and its process group (equal to PID because a
new session was requested). Events have UTC and monotonic elapsed timestamps.
Periodic samples retain byte growth, hashes, first/last data timestamps, per-pipe
EOF, and the direct process's separately observed exit. Reader failures retain
their original exception type and a bounded message. The sample interval is
between 0.01 and 1 second; this bounds periodic sample count over the command
and cleanup allowances. Stream byte limits bound chunk capture and retained
decoded strings. There is no recursive filesystem walk or process inventory.

A literal final `Test Suite 'Selected tests' passed/failed at ...` line is a
diagnostic trigger only. After its configured grace period, at most one capture
records whether the direct child is still live, which pipes remain open, byte
growth, and the owned result marker state. That grace period does not extend
the command deadline. No capture runs after the command has already completed.
The final selected-suite text can say "passed" while the wrapper still times
out or returns a nonzero exit. Neither that text nor a result marker creates an
XCTest, bridge, native, carrier, OTA or release verdict.

`owned_result_root` must be an existing canonical directory owned by the current
user. `result_bundle` must be its initially absent direct `.xcresult` child.
Observation uses an anchored directory descriptor and `O_NOFOLLOW`, reads no
file content, and records only shallow metadata for that bundle and its direct
`Info.plist`. Symlinks are reported as symlinks and never followed. Presence is
not official result validation. The caller is responsible for supplying the
owned ephemeral result root; the observer cannot attest the caller's ownership
claim or authorize cleanup of arbitrary paths. It removes no result files.

## Deadline and cleanup

The command allowance is finite, positive and at most the existing 600 seconds.
The monotonic command deadline starts immediately before launch. It is never
reset by suite output, result markers, log growth or observation. On timeout,
`subprocess.TimeoutExpired` retains the original argv and requested timeout,
plus raw captured bytes. Other original failures propagate after cleanup.

Cleanup sends TERM only to the recorded owned process group, waits at most the
original eight seconds, then sends KILL to that same group and waits at most
eight more seconds if needed. Cleanup observation does not authorize another
command run or extend the command allowance. It continues even if a diagnostic
write fails. No `ps`, `sample`, shell, process enumeration or subprocess sampling
is used. The observer polls only its owned `Popen` handle and uses signal 0 on
the recorded owned PGID to observe group existence without enumeration.

Failure cleanup is complete only when the direct child has exited, both pipes
have EOF, and that recorded group is absent. A descendant can close both pipes
and ignore TERM; the eight-second escalation still applies to its owned group.
A present-or-zombies group or an unknown probe result cannot establish absence
and leaves cleanup incomplete after the bounded waits. Failure paths check the
group even when the direct child had already exited with both pipes closed.
Normal successful command completion preserves the original communicate
contract (child exit plus both EOFs), and does not imply group absence; the
separate observed group state and unattempted cleanup remain explicit.

The inherited-descriptor case is explicit: a direct child may exit while an
owned descendant keeps a pipe open. This wrapper records that distinction and
still waits for EOF within the same deadline. On interruption it signals the
recorded group even if the leader has already exited; this avoids the old
cleanup branch that attempted another `communicate` when `poll()` had already
returned. It cannot terminate a descendant that deliberately leaves that group;
after the two bounded cleanup waits, unresolved cleanup remains recorded as
incomplete and the original failure still propagates. That limitation cannot
grant acceptance. No other project's process is intentionally addressed.

## Reproduction and evidence

Run from the repository root:

```sh
python3 -B verification/apple-command-finalization-observer-v1/verify.py --source-revision-context dcae16aa53627ce9589a7064418aad7b795bedb1
```

The revision is a root-supplied context label. `receipt.json` binds the exact
uncommitted observer, tests, verifier and this document by SHA-256, byte count
and mode; the manifest digest is the source authority. The verifier binds the
two read-only references separately, records the actual Python executable/hash,
version, command, cwd, stdout/stderr and scope, and verifies that source and
reference bytes did not change during the host suite.

Host controls use only owned harmless Python children: normal exit, exact
cwd/env/session identity, nonzero/check behavior, live child after suite output,
result marker growth, exited child with inherited pipes, inherited-pipe timeout,
TERM cleanup and actual eight-second TERM-to-KILL escalation, split UTF-8/CRLF,
closed-pipe descendants that ignore TERM after a failed leader exits,
decode/reader failures, per-stream overflow, interruption and symlink/path
rejection. Temporary directories stay inside this lane's `scratch/` and are
removed after each test; the empty scratch directory is removed by verification.
No simulator/device inventory, boot, runtime, compiler, build, UI, screenshot,
capture, service, global file or Git operation is part of these controls.

This receipt is host evidence only. It is not native or physical-phone evidence;
phones remain disconnected and deferred. Future root review, explicit native
selection, integration, official result export and all product/GA gates remain
separate and ungranted.
