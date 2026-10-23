# Monotonic host deadline repair

The host previously depended on a separately scheduled relative watchdog. A late
result could win if that watchdog started late. The independent derived-source
reproduction and candidate checks remain in
[`verification/capability-deadline-review`](../../../verification/capability-deadline-review/README.md).
The production repair uses exactly the independently tested Host bytes.

The host now captures one absolute monotonic deadline before scheduling work,
checks it before invoking an adapter and when choosing a result, and sleeps the
watchdog until that same instant. Pre-invoke expiry supplies the installed
adapter's explicit no-I/O exit fact; invocation return still supplies the other
fact. Previously chosen terminal results stay immutable.

`receipt.json` identifies 49 source files by content, all command/tool versions and
logs, and the unchanged source snapshot. The actual SDK passed 45 tests in debug
and release, 25 native HTTP/exit/deadline tests under Thread Sanitizer, iOS arm64
library compilation, Android API28 public-probe linking and WASI value-module
compilation. The new public-API regression deliberately stalls a delivery
callback to delay actor processing: the earlier success remains final and the
other result becomes deadlineExceeded. Its initial Swift isolation compile error
and source are retained separately; they are not reported as passing.

Reproduce from the repository root:

```sh
python3 verification/tools/qualify-host-deadline.py
```

This is neither a hard real-time dispatch guarantee nor rollback of committed
effects. Cross-compilation does not execute on phones. Guest/C integration,
activation, signed distributions, FieldLog plugin adoption and launch gates remain
open. The independent codec review covers its earlier immutable source snapshot;
the root integration receipt separates that evidence from this repair.
