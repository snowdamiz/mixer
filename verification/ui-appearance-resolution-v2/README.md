# V2 resolution data evidence

`candidate-1/receipt.json` binds 69 frozen inputs, 26 commands and 14 compiled
module/library/executable outputs. Full SDK Debug and Release each passed 127
observed tests: XCTest 8; Swift Testing MixerUI 107, MixerCore 10, MixerApple 2.
The 107 MixerUI Swift Testing functions include 21 new V2 resolution tests.
Public consumers execute separately under Debug/Release host compilation and
compile against public modules for iOS and official Swift Android targets.
Four expected negative public-consumer compilations demonstrate immutable output.

The original producer `sdkTestCounts` field captured only the first Swift Testing
target summary (107). `candidate-1/count-audit.json` explicitly supersedes that
field by checking all three Swift Testing summaries against actual distinct passed
functions and their frozen target ownership, plus actual XCTest passed cases.
Nested XCTest suite summaries are not added together. Producer inputs, receipt
and command logs remain unchanged. The count audit records its own command, cwd,
Python version, source digest and source/log bindings.

Reproduce with a new candidate directory, then audit its counts:

```sh
python3 verification/ui-appearance-resolution-v2/verify.py candidate-new
python3 verification/ui-appearance-resolution-v2/audit-counts.py candidate-new
```

The count auditor deliberately checks the current frozen suite's observed target
counts. Update its expected counts explicitly when later product tests change.
`.build` outputs are local ignored scratch artifacts; their exact hashes remain
in the receipt. No compiled artifacts are reused between candidate variants,
build configurations or target platforms. `inputs/` retains the actual tested
source bytes; its manifest, source revision and digest identify the tested local
candidate even before a coordinating commit.

Initial exploratory compile/test logs outside `candidate-1` are not qualification
receipts. The first exploratory compile ran before the new test file existed and
reported no matching filtered tests; candidate-1 uses the complete frozen suite.

Scope is public untrusted immutable data resolution only. Internal native capture,
concrete build support, measured text/layout, widget consumption, atomic native
transactions, signed display/input/health, physical parity, separate-repository
published FieldLog packages and GA gates remain pending. No phones were discovered,
used or requested for reconnection.
