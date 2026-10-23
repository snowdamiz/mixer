# Presentation test actor-isolation repair

The existing `nativeTree` local function in
`GuestUIPresentationWindowTests.swift` now explicitly declares `@MainActor`.
Hosted CI on Swift 6.2.4 rejected the unannotated function because it reads
`NSView.bounds`, `window`, `isHiddenOrHasHiddenAncestor`, and `subviews`.
The repaired file SHA256 is
`e44f6a21b3fbd0417ae818328845e5121b2dcabe853504ba2c2d8fa6de8ea9fd`.
The exact one-line change is retained in `repair.patch`.

`verified-2/receipt.json` records successful compilation and execution of the
actual existing model and window tests in Debug, Release (`-O`), and TSan with
Apple Swift 6.4, Xcode 27.1 (27A9275). Each mode reports 14 tests: 13 pass and the
visible-window opt-in test is explicitly skipped. The hidden/detached native
window test runs. There is no additional compile issue on this local toolchain.

The commands reuse the byte-identical complete activation production modules
from `verification/common-presentation-lifetime/final-1/receipt.json` and the real
Swift/C dependency objects and VM archive recorded by that receipt. They compile
the retained actual `GuestUIPresentationModelTests.swift` and `TestMain.swift`
with the frozen repaired window test. Commands, logs, tool versions, qualified
source digest, retained source/module/dependency hashes, and test executable
hashes are recorded. The runner verifies all retained inputs before execution
and again after execution. Each run uses its own compiler cache and output
directory; the owner build is not overwritten.

The initial source snapshot matched all 23 retained activation production files.
Before the final run, a concurrent edit to
`CapabilityGuestUIPresentationLifetime.swift` changed the workspace source.
The receipt records that drift and makes no claim to compile or qualify that
concurrent implementation. TSan instruments the newly compiled test executable
and reuses the prior instrumented activation module; retained dependency objects
remain uninstrumented.

The earlier hosted failure remains recorded in
`verification/github-ci-f19a18b/receipt.json`, with its log hash and URL bound in
this receipt. The available local toolchains are Swift 6.4 and Swift 6.3.3;
Swift 6.3.3 was inventoried only. Pinned hosted Swift 6.2.4 revalidation after
the fix remains pending. These host tests do not establish positive visible
display, physical iOS or Android, immutable published-package consumption,
signing/store/release/customer/operational, or GA qualification. No device
discovery or runs were attempted.

Reproduce with a fresh run name after the retained input prerequisites exist:

```sh
python3 verification/presentation-actor-ci-repair/run.py fresh-run-name
```

`run-1/receipt.json` preserves an incomplete first attempt: the actual Debug
executable passed, but the verification parser counted the aggregate test-run
summary as an extra test and stopped. `verified-1/guard-failure.json` preserves
the subsequent production-source guard stop before any commands ran. The final
runner excludes the summary from the test count and explicitly records
concurrent workspace production drift while qualifying the retained module.
