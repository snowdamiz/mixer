# Hosted identity startup independent review

Correction is required before accepting the frozen startup candidate. Fresh
macOS and isolated Linux normal suites passed, and the source/evidence bindings
are complete. Independently authored adversarial tests found one inherited
endpoint-validation defect exposed through the new operator configuration path.
The producer packet remains unchanged and unapplied by this review.

The reviewed patch is
`482e3aa35c7302a9bf418a7c42a2637a41a88230fe506de873e8b79cc513ece8`.
Applying it to accepted `b0629cf5` hosted source reproduces the frozen 68-file
source digest
`c844efdf610f66280ef04cd5a47d033aad13105f60823e3eef60ba771fb026e2`.
All 197 producer output bindings, ten overlay files, source archive entries and
914 dependency files match. The dependency digest is
`99bc0e5256ca834e5cd24bfcd3a1f5b158d5479af5677cccbe998ee005628452`.
The source reconstruction preserves the accepted portability and run-local
metrics repairs; historical metric packets were not overwritten.

`verification/hosted-identity-startup-review/receipt.json` is the review closure.
It binds this document, commands, tool versions, exact sources, output logs and
cleanup. The review owns only this document and that evidence directory.

The actionable finding is **IR-F01, invalid endpoint LF accepted**. Existing
`Identity.Manifest` host-label validation at line 56 and path validation at line
63 use `^...$`. The regex end anchor accepts a final newline. Consequently,
`StartupConfig.load!/3` accepts an otherwise valid configured JSON envelope whose
`jwks_endpoint.host` is `keys.independent.invalid\n`, or whose path is `/keys\n`.
The converted entries also pass direct `Manifest.validate/1`. CRLF variants
reject. This defect is present in the unchanged accepted Manifest source, rather
than introduced by a changed validator in this patch; the startup constructor
exposes that validator to the explicit operator JSON input.

`endpoint-probe.log` records these exact synthetic inputs and outcomes.
`endpoint_regression_test.exs` and `endpoint-regression.log` contain four minimal
expected-rejection regressions: direct Manifest and StartupConfig for each of
host LF and path LF. All four fail against this frozen candidate.
`review_startup_adversarial_test.exs` supplies nine independently authored cases;
both platforms pass eight and fail IR02 at endpoint host LF. Failed runs are
preserved and are findings, not skipped or passed checks.

The bounded correction is to change both Manifest expressions to strict
whole-string anchors `\A...\z`, add direct Manifest and StartupConfig endpoint
regressions with valid controls, and repeat the relevant hosted/release/Linux
checks. No transport rewrite is needed to establish this configuration-rejection
failure. This review does not claim successful unsafe network authority from the
malformed input. Root has assigned the correction to a separate isolated packet;
this review does not accept that future packet in advance.

| Check | Independent observation |
| --- | --- |
| IS01 defaults and role separation | Passed. Actual disabled API has liveness and no owner; disabled processor has no endpoint/owner and retains processor queues. Stray identity JSON rejects even with absent mode. |
| IS02 exact JSON and limits | Normal tests passed; adversarial tests confirmed duplicate/escaped duplicate rejection at every nesting level, closed fields, integer-only values, byte/profile/resolver limits, exact binding, fixed enum conversion and zero atom growth over 900 invalid dynamic-string submissions. Endpoint LF rejection fails as IR-F01, so this case is not accepted. |
| IS02 resolvers and CA | Passed. Canonical private/loopback/IPv4/IPv6 resolvers retain fixed port 53. Alternate spellings, zones, ports, trailing control/space and duplicates reject. Runtime uses one OTP CA result, normalizes combined-cert entries for identity DER validation and preserves the original CA list for database TLS. Invalid constructor roots reject; no environment CA/fixture/module bypass exists. |
| IS03 application wiring | Passed. Explicit runtime setting required by actual Application; configured owner component starts before Endpoint. Empty snapshots/attempts/flights and zero startup fetches observed. Missing setting or invalid owner prevents endpoint startup; production constructor rejects test-only options. Two-argument compatibility helper is explicitly disabled. |
| IS04 configured public adapter | Passed for valid configuration. Actual Linux Application/Endpoint/PostgreSQL starts; public `ConfiguredVerifier.authenticate/2` cold-admits a synthetic signed token through production DNS at port 53 and verified HTTPS at port 443 in a network-none namespace. Disabled bound profile rejects without a flight. |
| IS05 lifecycle | Passed. Actual owner kill restarts empty with a new epoch and worker supervisor; application shutdown removes owner/endpoint. Linux replay rejects old leases, cold-admits after restart and cancels/closes an active fetch on shutdown. |
| IS06 build and source receipts | Passed for normal suites: macOS 85 passed plus two Linux-only skips; Linux 87 passed with zero skips. Production release built; missing runtime config exits 1 as required; test-only owner/transport/startup fixture exports are excluded. |
| Error/Inspect privacy | Constructor failures have fixed bounded categories. StartupConfig and RuntimeConfig Inspect omit trust/environment contents. No new production logging is present in the changed modules. This is scoped evidence, not a blanket claim about every possible VM crash dump. |

The full Mac run used the frozen local collector in an owned source copy and
owned loopback PostgreSQL database. The Linux replay used pinned existing
Elixir/PostgreSQL images with no external network, an owned namespace and
synthetic CA/DNS/TLS fixtures. Both normal suites replay accepted component tests;
the changed startup wiring additionally has actual application/lifecycle tests.
The independently authored tests are additional isolated inputs and never enter
live hosted source. Tools and commands are recorded in `state.json`, the host
collector receipt, `linux-receipt.json`, and the tool logs.

Owned PostgreSQL instances stopped, owned containers and Linux/Mac source
scratch were removed, and Linux fixture cleanup found no retained TLS key
directories. Other projects' processes and data were preserved. No commit/push,
live hosted source change, production publication, credential change, native/UI
run or physical-device run was performed by this review.

This is development-slice evidence only. Synthetic loopback PostgreSQL has no
TLS; production database TLS is configuration evidence. No real identity
provider, authenticated HTTP route, provider selection/discovery, membership,
permission, durable identity registry, Neon/Cloudflare operation, native or
physical qualification, FieldLog dogfood release, external customer operation or
GA acceptance follows. Physical phones remain disconnected and deferred.
