# Independent root metadata SPI review

The original external `probe.swift` imports the public module with its named SPI;
it does not use `@testable` or internal constructors. It passes 204 checks against
the retained Release library, including all 154 shared malformed manifest cases
and 36 assignment cases. The manifest cases are re-signed and bound to their
exact modified artifact so an earlier digest mismatch cannot mask shape checks.
Only public synthetic fixture keys are used.

Additional checks cover exact snapshots and metadata, verifier context identity,
payload corruption, stored/high-water sequence consistency, explicit revocation,
and expired signing windows. Ordinary current-time verification remains strict;
only the retained metadata path omits time windows.

`audit.py` matches 71 live/export inputs, 31 expected command results and logs,
87 owner evidence files, twelve retained artifacts, forty unchanged old paths and
the exact old v3 source after removing its three marked additive blocks. It seals
the root command logs, probe source, actual binary and linked Release archive in
`receipt.json`. It does not rerun production code or modify the owner seal.

The SPI cannot prove that a record was previously committed healthy. The private
updater must establish that provenance and keep its verifier context private.
No execution, durable selection, platform runtime, publication or GA gate is closed.
