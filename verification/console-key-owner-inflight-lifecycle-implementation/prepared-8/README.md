# Prospective exceptional refused-wrapper exit correction

prepared-8 addresses CCT7-01 only in the wrapper exit boundary and its no-process
check. Prior packets/results remain immutable. All25 canonical input pins, nine
product methods, 18 real artifact schemas, dependency closure and sticky custody/
observe-only logic remain unchanged. Both plans remain unreleased; no successor
control, compiler, native child, process probe or TLS run has occurred.

The real entrypoint calls process_authority.refusal_exit_boundary. Its outer
try/finally always selects self-os._exit when refusal is set, whether main returns
or raises. Result defaults to125 and changes only after main returns a valid
integer. The boundary does no diagnostic I/O before self-exit. It reads both the
explicit refusal flag and retained active Authority. The actual Popen is held
globally immediately after creation, before later signal/evidence/close code.
Thus stdout.close or diagnostic delivery failure cannot bypass the self-exit
selection and fall through to ordinary Popen destructor polling. As before, this
is not a guarantee against arbitrary OS/interpreter failure of os._exit itself.

Last stderr diagnostics use a nonblocking descriptor, at most65536 bytes and50ms,
further bounded by the shared cleanup deadline. Missing/failed delivery remains
incomplete evidence; there is no unbounded final flush ahead of refused self-exit.
No last-chance diagnostic is attempted by the outer guard itself.

A sixth injected no-process subcheck invokes that exact shared exit boundary with
a retained synthetic child and sticky refusal. Two exceptional tails model
stdout.close and stderr diagnostic-write failure. Both require self-exit125,
retained child, no ordinary-finalization callback or child process callback, and
unresolved authority. The self-exit callback raises a control-only sentinel to
model its nonreturning selection; no os._exit or process operation executes in
this injected check. This qualifies only the selected branch predicates after a
future released control run, not actual interpreter destruction or historical
permission failures.

The control plan still has18 named cases, two VM-helper checks, ten ACKs, eight
custody fake children plus two helper children, zero added synthetic processes,
one MiB combined artifacts and40/46/52/55 cutoffs. Six injected checks replace the
prior five-check count. Local real runtime still refuses before launch because
frozen JOSE1.11.12 differs from canonical1.11.13. No shared dependency rebuild,
collector/CI edit or product change is included. The retained remote CI source
assessment is a separate root selection.
