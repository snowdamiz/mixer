The exact retained Phoenix CI log is bound by `beforeimage.json`. Its six failures
occur in the old fixture helper's `on_exit` stop after the test body completed.
The owner now traps parent exits, so direct test-process ownership and a second
conditional stop compete during teardown.

The canonical correction gives ExUnit a temporary owner child with infinite
shutdown. Its worker supervisor starts first, so ExUnit stops the owner first.
The helper captures the owner PID, worker PID and admission table before each
test and uses assertions-only `on_exit` checks after supervised teardown. K07g
also requires no replacement after its intentional owner stop.

`prepare.py` only hashes and copies bytes under a 55-second offline budget.
`prepared-1` freezes the accepted prepared-3 eighteen-file product closure,
current complete KeyOwnerTest and three current unchanged support modules,
dependencies, tool pins, bootstrap, bounded OpenSSL logger and runner. It never
binds this lane to the other lane's active canonical supervisor.

The single host VM compiles all 29 KeyOwnerTest methods and includes exactly the
six CI failures plus K07g. Expected ExUnit counts are total 29, excluded 22,
executed 7, skipped 0 and failures 0. The selected methods exercise actual local
TLS, admission, rotation, bounded storms and suspended-controller cleanup.
Excluded methods do not count as passes. The VM checks read-only formatting.

The OpenSSL shim logs exact argument vectors and capped successful output for a
version probe plus the fixture's three certificate commands. The real pinned
tool remains in the runner's exact owned process group. No private key bytes are
retained; fixture creation removes its private-key directory in an `after` block.
The bootstrap checks that its scratch-local fixture directories are gone.

The runner requires a separate root-authored release bound to the exact plan
SHA256, allows one output directory creation, keeps the prior 40/46/52/55-second
work/cleanup/finalization/receipt limits, strictly validates all eight required
artifacts, rechecks original pins, and only deletes scratch after exact child
reap and group absence. No process inventory is permitted.

Preparation is not runtime evidence. Compiler, formatter, OpenSSL and tests await
independent root review and release. Full Phoenix CI, native/device checks,
production operation and GA remain outside this targeted host receipt.
