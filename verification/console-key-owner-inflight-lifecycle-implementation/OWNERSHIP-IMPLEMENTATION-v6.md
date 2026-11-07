# Prospective artifact-bound and direct-VM cleanup correction

prepared-6 preserves the accepted CIR-01/02/03 custody implementation and addresses
CIR5-01/02 in control bounds and direct VM cleanup only. All nine product methods,
canonical source pins, 18 real artifact schemas, 18 named controls and prior
packets remain unchanged. Both new plans are prospective and unreleased. No
control, helper child, compiler, formatter, OpenSSL or TLS work has run.

The controls now enforce the selected exact 1048576-byte combined artifact cap,
including their terminal report. Per-file checks remain stricter than the plan.
Ten custody ACKs, eight custody fake native launches and two direct helper fake
launches are finite maxima. The shared global work40/cleanup46/post52/terminal55
bounds remain unchanged, with one fake/native fixture active at a time.

vm_cleanup.py is shared by the real runner and two subchecks within the existing
happy/native-timeout controls. It retains the exact Popen child and expected
PID/PGID/SID from its private session. Once Popen wait/poll reports completion,
that state is permanent: cleanup only observes group absence and never sends
TERM/KILL to the saved numeric PGID. Normal completion with an unresolved group
fails and preserves scratch. A running child can receive group TERM/KILL only
while poll still reports it running and its retained PID/PGID/SID remains current;
that authority is checked again before escalation. Leader loss or terminal group
absence never re-arms. This is not an atomic OS process-generation handle.

EPERM closes active cleanup authority permanently. There is no alternate PID
kill/API or later retry of that permission failure. Exact failing call, errno and
name, strerror, exception type/message and full traceback are retained alongside
PID/PGID/SID and time. Lost identity, permission failure, incomplete wait or group
absence makes cleanup uncertain and preserves scratch. The separate registered
wrapper-group custody protocol remains byte-for-byte unchanged.

The completed-child subcheck waits for a bounded fake child and requires no active
signals. The running-timeout subcheck observes a real 50ms wait timeout on a bounded
active fake child, then requires retained-identity TERM, exact reap/group absence
and no uncertainty. Each uses this same shared helper. These are two subchecks of
the existing named cases, not product methods or new named cases. Their exact
commands and typed cleanup observations are retained. The prior actual wrapper
TERM case remains separate.

The helper signal/EPERM paths and all control assertions remain source-only until
an exact root release. Output overflow, missing completion, late/partial
registration and INT/HUP remain pending. No new security, product cleanup,
application, DB, native/UI/device or GA qualification is claimed. Independent
review must select the exact control plan before any run and separately consider
the real runtime plan after inspecting actual terminal evidence.
