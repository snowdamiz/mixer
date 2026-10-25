# Command observer V2: cleanup with check=False

This derivative preserves the accepted V1 command, timing, stream and diagnostic
contract. The sole behavioral correction is on a normal nonzero child exit:
a surviving owned process group is retired even when `check=False`. The caller
still receives the original exit code and decoded stdout/stderr. With `check=True`
the existing assertion remains. A zero exit keeps the original communicate-like
semantics; the separate process-group observation is not proof of cleanup.

The failed-command cleanup retains the original eight-second TERM grace and
eight-second KILL grace. Its completion condition requires the recorded leader to
be reaped, both streams at EOF, and the recorded owned process group absent.
Unknown or zombie/group ambiguity remains incomplete. No arbitrary PID, systemwide
process enumeration, new native command, or authority/catalog dependency is added.
The command deadline remains at most 600 seconds; cleanup is separately bounded.

V1 and its receipts remain unchanged. V2 adds a host control in which a nonzero
leader exits while its same-group descendant has closed both output descriptors
and ignores TERM. The control requires actual KILL escalation after eight seconds,
absence of the owned group, and unchanged exit/output under `check=False`.
All inherited controls are retained. The exact current source and host results
are in verification/apple-command-finalization-observer-v2/receipt.json.

This is standalone host diagnostic tooling. It is not yet a selected native run,
a fix for UIKit focus behavior, or an explanation for the earlier Xcode stall.
No simulator, device, UI, screen capture, provider or GA acceptance follows.
