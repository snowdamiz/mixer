# Resolution v4 normal-exit correction

This source-only successor preserves every earlier sealed packet and zero
dependency-controller executions. It does not establish the cause of the
separate Swift attempt's EPERM or change that failed receipt.

When WNOWAIT reports a command exited, the controller now reaps it **without
TERM/KILL** and only observes process-group absence. A remaining or inaccessible
group fails closure and preserves scratch. Cancellation/timeout may signal only
an unreaped child last observed running; WNOWAIT is checked immediately before
each signal. If exit is observed, cleanup switches to the no-signal path.

Custody errors record the exact Python syscall/API boundary and arguments,
errno/name and a bounded chained traceback. A 32-entry trace records recent
calls; each traceback is bounded to 8 KiB with explicit truncation evidence.
EPERM permanently refuses further cleanup for that child. There is no alternate
kill method, permission bypass, process probe or retry.

The five exact commands, 55-second 40/46/52/55 cutoffs, root-selected plan SHA
argument, verified in-memory control bytes, private DNS/file inetrc, unchanged
shell HOME, private BEAM home, two selected package versions, nineteen unchanged
lock entries and signed-registry/TLS checks remain selected. The finite signal
cutoff and failure-preservation rules remain.

Static AST, source-order and byte-custody checks pass. This controller was not
imported or executed; no runtime/process probe or lock generation occurred.
`preparation-receipt-v4.json` records the exact proposed release argv. Root's
focused review and explicit release remain required. Functional/remote CI and
the two HTTP/2 wire checks remain separate pending qualification.
