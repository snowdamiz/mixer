# Private webhook transport regressions

Seven permanent host tests now protect the integrated private transport's
sanitized logging boundary and refusal before adapter reads. They cover exact
message/metadata reconstruction, raw and extra report rejection, integer/schema
edges, refusal to invoke arbitrary callbacks, the inactive ordinary application,
and absent or forged caller permits. Production modules are unchanged.

The existing release collector now checks all four transport modules and exact
entry-point exports, excludes producer/reviewer/permanent test helpers and
clock/adapter seams, and verifies that the transport role remains inactive.

An isolated full hosted run passes 149 tests, with two existing Linux network
namespace fixtures skipped explicitly. Formatting, compilation, release build,
missing-config refusal and release exclusions pass. Its 73-input source closure
is `1b2f03d474f825a6265e0a10f9baf2adda62dffe6c747542207f32753b4df997`.
PostgreSQL and owned process groups are stopped; 64,146,951 bytes of scratch are
removed after identity and open-holder checks. Commands, tool versions, source,
outputs and cleanup are retained under
`verification/stripe-webhook-transport-regressions/attempt-1/`.

Root applied only the tested test file and collector changes. The acceptance
receipt and read-only `verify.py --live` bind that exact source. Prior 72-input
integration and CI receipts remain historical; their `--live` checks no longer
describe this expanded test closure.

These regressions do not repeat or replace the independently reviewed wire,
deadline, sink and connection-disposal matrix. The role remains inactive. Public
admission, deployment resource ceilings, trailer policy, TLS/ALPN/ingress,
durable inbox and Oban reconciliation, provider qualification and G23 remain
pending. No billing route, provider mutation or GA acceptance is introduced.
