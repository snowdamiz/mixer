# Framing timeout-control startup synchronization

CI run 40406899898 at c4c6f3d8 fails its Swift selection-regression step because
the 150 ms timeout fires before a new Python interpreter prints `started`.
The other five jobs pass; later Swift steps are skipped. The original raw job
log and terminal job snapshot are retained. No retry is used to erase this result.

The unchanged original test fails identically when its owned child has a 300 ms
startup delay. The repaired test explicitly waits for the real parent and its
descendant to become ready, with a separate bounded startup check. It then calls
the real wait with the unchanged 150 ms timeout. Production runner code,
workflow limits and product deadlines are unchanged. Startup failure still
fails the test and invokes the runner's owned-process cleanup.

All 63 CI selection tests pass. Two negative controls confirm that killing only
the parent is detected through the released descendant's marker, and that failed
startup remains a failure with the parent reaped. Independent source review
finds no concrete issue and repeats the actual timeout test successfully. The
three released independent records are copied byte for byte into this packet.

This is host test-harness evidence only. No native runtime, UI, capture or
process inventory is used, and no Android integration or GA gate is accepted.
