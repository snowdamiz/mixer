# Hosted identity contract evidence

Owner scope: `docs/hosted-identity-contract.md` and this directory only. All source,
specimen, fixture and recording code is independently authored. No new runtime
dependency was added. Existing Elixir/OTP, Python and Go host tools were used.

`input-manifest.json` identifies the initially captured source files, per-file
SHA-256, canonical manifest digest and observed source revision. `inputs/` retains
those exact bytes because the shared checkout has active lanes. The final plan
header-only change and final reviewed plan digest are explicitly reviewed in
`plan-drift-review.json`; its diff and copy are retained. Do not treat the source
snapshot as a new implementation or edit it to match a later checkout.

Run `python3 verification/hosted-identity-contract/record.py` from the repository
root. `receipt.json` records commands, working directory, output hashes, exit
status, timeout, tool versions, reviewed source and artifacts. `commands/` contains
full stdout/stderr, including the meaningful expected Elixir compile failure.

The Elixir declarations use the isolated `MixerHostedContractSpecimen` namespace
so they do not define or collide with root's `MixerHosted` application. Their four
ExUnit assertions check declaration/data shape only. The negative check confirms
that role/tenant fields are not declared on the proposed verified identity; it is
not proof that trusted BEAM code cannot forge a struct. There is no verifier,
authorization policy, database, token issuer or fake integration implementation.

The focused Go race regression runs the existing config-ownership and tenant/
public-delivery tests. It preserves the observed b15ff7a behavior and supplies no
hosted identity, Neon, Cloudflare, PostgreSQL-membership, signing, CI-provider or
production-gate evidence. No native runtime, simulator, emulator, computer use,
cloud resource or external message was involved. Test subprocesses terminate.

Novel protocol claims in the contract cite only official OIDC, IETF, PostgreSQL
and Ecto documents, accessed October 24, 2026. Bounds, role defaults, error privacy,
locking and first-slice scope are proposed Mixer policy, not claims that those
specifications prescribe product behavior. The entire product plan remains scope.
