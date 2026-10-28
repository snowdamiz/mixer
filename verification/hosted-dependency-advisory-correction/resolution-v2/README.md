# Bounded resolution successor

The original sealed preparation is unchanged. This successor replaces its
300-second operation with one 55-second cumulative operation: stop work at 40,
finish owned-group cleanup by 46, finish source rechecks/scratch deletion by 52,
and finish the receipt by 55. Each of the same five sequential tool/Mix commands
has only the remaining work budget. There is one attempt, no retry or wider
unlock.

`resolution-plan-v2.json` pins `controller.py` and the original selected input
packet. `preparation-receipt-v2.json` and `source-review.json` bind the source
review. Python AST parsing and manual source review pass; the controller has
not been executed. Root must review/release the source before invoking its
recorded `python3 -B ... --root-release` entrypoint.

The controller keeps child leaders unreaped while signaling their isolated
groups, then reaps and observes group absence. It never signals a reaped group.
Unknown closure preserves scratch. Bounded logs and every failure are retained;
disk scanning/deletion use only the marked private tree. OS syscalls are not a
real-time sandbox; a deadline/closure failure is not a pass.

Success requires an actual Mix-generated 21-entry lock, the selected two pins
and official outer checksums, all nineteen other complete-entry hashes
unchanged, and an identical lock after the offline locked recheck. The receipt
and separate `lock-inventory.json` retain all entries and nineteen before/after
hash pairs. Canonical/shared dependency files are never written.

No product compilation/test/start, local broad callback/authority harness, DB,
provider, OpenSSL CLI, native/UI or capture operation is selected. Full remote
Phoenix CI remains later validation; the two HTTP/2 wire qualifications remain
separately pending.
