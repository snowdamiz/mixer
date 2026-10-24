# Configured identity startup endpoint correction

This isolated candidate corrects the inherited `Identity.Manifest` endpoint
validation defect exposed by the configured-startup slice. The original frozen
startup candidate admitted the synthetic host `keys.independent.invalid\n` and
path `/keys\n` through both `Manifest.validate/1` and `StartupConfig.load!/3`.
This is observed configuration acceptance. No unsafe connection, request smuggling,
SSRF or successful transport exploit is claimed.

The only production correction replaces `^...$` with `\A...\z` in the two
Manifest regular expressions for a host label and endpoint path. Terminal LF is
then outside the permitted character match. The original character grammar,
label/host/path byte limits, port policy and dot-segment rejection remain in
place. Transport, resolver, TLS, key-owner and startup implementation are unchanged.

`verification/hosted-identity-startup-correction/implementation.patch` is the
cumulative candidate against the current unchanged live hosted tree.
`correction-vs-frozen.patch` is the exact two-file difference from frozen startup
source digest `c844efdf610f66280ef04cd5a47d033aad13105f60823e3eef60ba771fb026e2`.
It contains only the two Manifest lines and the new separate
`manifest_endpoint_test.exs`. All ten original startup overlay files retain their
original hashes, including the accepted portable TLS fixture use and run-local
metrics collection. No dependency, dependency pin or installed live source changed.
The original startup packet is preserved.

The new executable tests exercise direct Manifest validation and configured JSON
startup separately. They reject terminal LF, CRLF, CR, tab, NUL, leading and
embedded newline samples; preserve accepted normal characters; accept the original
one-byte host, 63-byte label, 253-byte host and 1/2048-byte path boundaries; and
retain rejection immediately beyond the size limits and outside the grammar.
With this identical new test file on the frozen source, the focused run reports
10/14 passing and four LF rejection failures. With only the anchor correction,
all 14 focused tests pass. The expected failing baseline log remains in the packet.

The corrected source digest is
`bfa2dcc1467f524a68fec298bdd098625f450b68ab2bd68b99f2a73d435772c3`.
The full macOS suite passes 93 tests with two explicit Linux namespace skips.
The production release builds, rejects missing required runtime settings with
exit 1, and excludes all four checked test-only owner/transport/startup exports.
The isolated Linux suite passes 95 tests with no skips. Fresh run-local metrics
record the actual configured application and endpoint, zero startup fetches,
production DNS/HTTPS cold signed-token admission, restart fencing, cancelled
inflight shutdown and closure of the three fixture connections. This replays the
existing normal production-path suite against the corrected candidate; it does
not send the invalid newline endpoints over a network.

The host run uses the frozen startup collector without changing it. The Linux
collector retains the established suite, pinned images and production namespace
fixture; only unique scratch/namespace naming, the platform temporary-directory
selection and a packet-local copy of the unchanged namespace helper differ.
No frozen metric output is reused. Commands, tool versions, source and dependency
manifests, archives, exact patches, output hashes and owned-resource cleanup are
bound in `receipt.json`. Root integration and fresh independent correction review
remain required; the candidate is not applied by this producer.

This is development evidence only. Synthetic PostgreSQL uses loopback without
TLS; production database TLS has configuration evidence only. Synthetic CA roots
are supplied only to the pure constructor in tests; runtime roots remain OTP's
standard source. There is no real identity-provider, authenticated HTTP,
membership, permissions, discovery, native, physical-phone, deployment, customer
operation or GA qualification. No gate is closed here.
