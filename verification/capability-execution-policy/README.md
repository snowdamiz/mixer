# Internal execution policy derivation

This helper revalidates enclosing fresh or retained metadata with the installed
material's original verifier context and the exact payload. It derives native
configuration and SDK dispatch policy, plus optional concrete adapter settings.
It creates no adapters, filesystem state, tasks, sessions or executable selection.
Actual committed-health provenance remains the private updater's responsibility.

Both the SDK dispatch policy and adapter admission intersect signed and installed
permissions, origins, methods and namespaces. Empty, missing or disjoint sets
deny; namespace case remains significant. Memory uses the downward page conversion
including zero. Fuel/startup narrow signed and installed bounds; other execution,
request and scheduling limits come from the immutable installed material.

Seven original policy tests plus seven I/O and sixteen material tests pass in
debug and release. The dispatch test uses the actual SDK host: an allowed request
returns unavailable because no HTTP adapter was supplied, while excluded requests
return permission denied. It makes no network request. Synthetic signed fixtures
use a publicly reproducible TEST ONLY key and are not executable Wasm.

Official iOS and Android modules and policy objects compile. A positive public
consumer typechecks; trying to name the internal policy type is rejected.
Independent source review found no actionable issue. It did not repeat the root
test run; `independent-source-review.json` records that boundary.

The 141-input export uses the committed private I/O and metadata SPI with the
previously qualified bridge. Unfinished store and new bridge lifecycle files are
excluded. Combined coordinator qualification, application links, physical-device
behavior, immutable distribution and all product gates remain pending.
