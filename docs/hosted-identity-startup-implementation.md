# Configured identity startup implementation packet

The implementation is isolated under
`verification/hosted-identity-startup-implementation/overlay/`. It has not been
applied to the live hosted source. The selected contract is
`docs/hosted-identity-startup-contract.md`; root must review the exact patch,
source hashes and observed receipts before applying it.

`Identity.StartupConfig` accepts the explicit disabled/configured environment
contract, decodes no more than 65,536 bytes through the accepted duplicate-aware
JSON decoder, converts only fixed known keys and values, and applies the accepted
manifest validator. It bounds generation, binding, profile count and distinct
canonical IP resolvers at fixed port 53. It validates every supplied DER root;
errors use fixed categories and Inspect exposes only the mode.

`RuntimeConfig` obtains OTP roots once, leaves the existing database SSL list
intact, and extracts DER from binary entries or the OTP combined certificate
shape for identity validation. Installed OTP 29/public_key 1.21.7 returns
`{:cert, DER, decoded}`; the first constructor attempt that revealed this is
preserved. `otp-ca-source.json` binds the observed type, installed source/spec
and BEAM hashes. No alternate production root source is added.

One `identity_startup` settings field is bound by runtime configuration.
`Application.start/2` fetches it explicitly and starts the accepted fixed-name
`KeyOwnerSupervisor` before the HTTP endpoint in configured API mode. The
existing two-argument helper explicitly selects disabled mode. Disabled API and
processor modes omit identity children. This packet changes no accepted owner,
verifier, resolver, address policy, transport or cryptographic implementation.

Tests boot the actual application, Repo, Oban and Bandit endpoint against an
owned synthetic PostgreSQL database; they test disabled API/processor behavior,
configured empty state and zero startup fetches, missing required bindings,
production constructor rejection, supervised owner crash/restart and shutdown.
The isolated Linux test configures the startup constructor with synthetic roots,
fixed DNS port 53 and a synthetic global-classified peer on an owned network-none
namespace. The public `ConfiguredVerifier.authenticate/2` performs cold signed
token admission through production DNS and verified HTTPS, then exercises warm
authority removal, old-lease rejection, cold restart and active-fetch shutdown.
No real identity provider is contacted and no production DNS policy is weakened.

`receipt.json` maps IS01–IS06 to exact final evidence. Earlier failed and
superseded attempts remain beside the final receipts. Source snapshots bind the
root-owned portability/metrics repair that was dirty at input capture. Tests
write accepted component metrics only to collector-selected owned directories.
Collectors stop owned PostgreSQL instances, remove owned containers and scratch,
and preserve unrelated services. Root-owned live hosted source is untouched.

These are development-slice receipts. Synthetic PostgreSQL uses loopback without
TLS; production database TLS has configuration evidence. This is no authenticated
HTTP route, durable identity registry, permission or membership implementation,
provider selection, discovery, customer operation or GA acceptance. Physical
phones, native lanes, production deployments and external qualification remain
outside this packet.
