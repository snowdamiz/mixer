# Runner revision for root review

The original runner, command roster and source freeze are preserved byte for
byte. The product source146, host11, all negative fragments and every inner
compiler/host/version argv are unchanged. `run_bounded_v2.py`,
`proposed-command-roster-v2.json` and `source-freeze-v2.json` are separate files.
No compiler, host product or version command has run.

The v2 runner puts all spawn, poll, capture and postrun pin work inside an outer
try/finally. That finally attempts exact owned-PGID SIGKILL, exact child wait
(with exact-PID waitpid fallback), reaping and group-absence verification even
when polling/waiting or immutable-input verification raises. A further outer
finally closes capture resources and retains a final write-once receipt with
fixed failure classifications. Receipt preparation errors are captured into the
minimal receipt; write-once start/plan/owned-process records remain independently
available. Filesystem refusal/failure itself can still prevent a receipt write;
the runner does not claim to repair an unavailable evidence filesystem.

stdout and stderr use nonblocking pipes. Each stored stream is a bounded prefix
of at most 4 MiB; no regular file can grow beyond the cap between polls. An
observed excess records output-limit and terminates the command. Drain after
termination uses the same cap and deadline. No process inventory is used. All
signals and waits name only the exact new-session child PID/PGID recorded by
this invocation.

The work deadline stays 51 seconds. Cleanup stops by 54.5 seconds, reserving the
remaining part of the 55-second ceiling for final evidence. Exceptions retain
failed receipts and never cause a compiler or host retry. The original command
ceiling remains 21 compiler commands, two filtered host runs and one version
query, with one globally coordinated compiler.

Root requested source-only preparation of this revision. Its exception handling
has been inspected as source; no runner failure-injection process or product
command has been launched. Root must review the v2 hashes and explicitly release
the v2 source freeze before execution.
