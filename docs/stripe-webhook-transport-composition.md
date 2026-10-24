# Private webhook transport hosted composition

Status: **normalized candidate passes isolated full-hosted composition; root
integration remains pending**. No live hosted source, route, role, dependency,
tracker or Git state was changed by this lane.

The producer seal remains
`a36676ab1ab9bf1d0f98077d86d7f375b7c46a18c13cdb4bcd1adb24ce5d430d`;
the independent review seal remains
`a3d8b7677ce58b23246c61e76e0db13806c5cc53a41c44fd06aa3a75376a4f81`.
The [root-selected contract](../verification/stripe-webhook-transport-root-review/selection.json)
and [independent review](stripe-webhook-transport-review.md) remain authoritative.
Neither upstream packet was rewritten or executed against its own directory.
Their read-only verifiers pass in each composition attempt.

The original reviewed module is
`62cd64f8711ff5296270b38a1c679336e075705bf5845c88d82d7e4bbd28aec0`.
[Attempt 1](../verification/stripe-webhook-transport-composition/attempt-1/receipt.json)
retains its failed formatter check. Root selected a separate formatter-only
normalization after that failure. The normalized module is
`56a26cf3a56f3e5a5b2d8f5104fc7c3371b0e44918b007197be5871cf94ef1a5`.
The [exact diff](../verification/stripe-webhook-transport-composition/attempt-4/formatter-only.patch)
changes two layout sites: a multiline function's `do:` indentation and
`Supervisor.init` keyword layout. It changes no non-whitespace character.
The executed [equivalence check](../verification/stripe-webhook-transport-composition/attempt-4/formatter-equivalence.json)
matches metadata-free ASTs and 4,344 tokens after removing source positions and
EOL whitespace tokens. It also accounts for the second source-position tuple
on Elixir's `not in` token. Root must inspect this exact normalization before
applying the module.

[Attempt 4](../verification/stripe-webhook-transport-composition/attempt-4/receipt.json)
adds exactly this one normalized module to the accepted 71-input baseline
`ac391070ec439ecfca288b9a7657aac1eada5bc1196efb8735211cc60a6883bc`.
The resulting 72-input digest is
`789b7de9b46ef2ce65ad83a4c916dde9a513a8eaa68dfc073e4c65ec97e2ee93`.
Capture remains byte-exact at
`a420d5a54868d61c3d6e9c7cb41807698eb729df3e6babda12135a727ac657ea`;
signature remains byte-exact at
`3fa0a2d8bee3e4eb9a4204857aaec0d16565df7c0d3f0aa8062158d51f2e3cb6`.
No test, collector, application, router, configuration, migration or lockfile
change is included in this source closure. Locked dependencies resolve unchanged.

The unchanged full hosted collector passes formatting, test-environment
compilation with warnings as errors, **142 tests**, production release creation,
expected missing-runtime-configuration rejection and existing identity/capture
release exclusions. The two existing namespace-fixture tests are explicitly
skipped on macOS: K03's production DNS/rebinding fixture and IS04/IS05's cold
configured-startup DNS/TLS lifecycle fixture. These are not passes. The retained
environment is macOS arm64/Darwin 27, Elixir 1.20.4, OTP 29/ERTS 17.1,
PostgreSQL 17.11 and Python 3.14.8; exact version outputs and executable hashes
are retained in the attempt.

The separate [production BEAM check](../verification/stripe-webhook-transport-composition/attempt-4/production-policy.json)
loads all four transport runtime modules from the freshly built release,
records their complete atoms/exports, checks exact top-level exports, and finds
no producer/reviewer test helpers, capture clock, test adapter, or extra capture
clock/adapter parameter. Runtime `Owner.snapshot/0`, `Sinks.snapshot/0`,
`Sinks.inventory/0` and supervision callbacks are exported intentionally; they
are recorded rather than hidden as test exclusions. The role remains inactive:
there is no transport owner, sink owner, guard supervisor or transport listener
started by this inspection. The unchanged full hosted suite exercises its
existing components and does not replay the private transport wire matrix.
Transport behavior/privacy evidence remains the separately sealed producer and
independent review evidence. The production check is evidence owned by this
packet; it is not yet a permanent hosted release-collector change.

Attempts 2 and 3 remain failed composition-harness checks, not candidate failures
or passes. Attempt 2 retained a secondary source position in the token comparison;
attempt 3 compared whitespace-separated strings and rejected inserted whitespace
beside `)`. Only this lane's harness changed. They failed before the first
collector wrote source archives. Their source closures are explicitly
[reconstructed](../verification/stripe-webhook-transport-composition/source-recovery/attempt-2/receipt.json)
from the original retained baseline/raw source and each attempt's actual exact
formatter diff, independently matched to the accepted normalized source. These
reconstruction archives are separate from the unmodified original failed seals;
they are not represented as original run archives. Attempt 4 retains its actual
source archive, dependency source archive, production release archive, production
and test application BEAMs, commands, outputs and all hashes.

All four attempts have no remaining owned command-group members or open scratch
holders and have removed identity-checked scratch. Attempt 4 stopped its isolated
loopback-only PostgreSQL fixture and removed 64,138,419 bytes of composition
scratch. The final supplemental check observes the fixture's port refusing
connections and its temporary data directory absent. Other projects' processes,
logger policy, native instances and data were untouched. No computer-use or
physical-device execution occurred.

This result supports root review of a private inert hosted module addition.
Public P11 resource ceilings, P12 trailer policy, P14 TLS/ALPN/deployed ingress,
P15 provider authority and delivery, P16 durable inbox/atomic Oban/billing
reconciliation, G23 and GA remain pending. There is no production publication,
provider/credential change, combined DB/domain migration, public acknowledgment,
catalog-inspector retry or authority-review retry.

```sh
python3 -B verification/stripe-webhook-transport-composition/verify.py
```

The verifier is read-only. `--live` additionally requires all 72 live inputs to
match the normalized composition after root integration. Replaying `prepare.py`
creates a new attempt and invalidates this frozen packet until explicitly reviewed
and resealed; do not replace or reinterpret the failed attempts.
