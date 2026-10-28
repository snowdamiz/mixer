# Two-pin dependency correction proposal

Prepared against `a4f1d13fe83415377e84b3fc33869e667da30fae`.
The [source patch](proposal.patch) changes only Bandit `1.13.1 → 1.14.0` and
JOSE `1.11.12 → 1.11.13`, plus their two third-party inventory references.
Proposed copies are in `proposal/`; original dependency files are retained in
`inputs/`. `dependencies.json` and a new lock are deliberately absent until
actual Mix resolution supplies their facts. The inventory references in the
proposal are pending references, not current acceptance evidence.

Preparation ran only Python/file operations. It verified that the prior sealed
advisory packet and all selected canonical inputs were unchanged. The private
two-file preparation scratch was removed; no process group or runtime was
created. [preparation-receipt.json](preparation-receipt.json) records the exact
inputs, static tool identities and cleanup.

## Selected resolution operation

[resolution-plan.json](resolution-plan.json) specifies the exact five sequential
commands, sanitized environment, private state paths, input/output bounds and
group cleanup. It remains **pending root's runtime-lane release**. The installed
filesystem identities are Elixir/Mix `1.20.4`, OTP `29.1.1` (Homebrew revision
`29.1.1_2`) and Hex `2.5.1`. The prior remote job used Hex `2.6.0`; local and CI
tool identities must remain distinct. No installation or toolchain change is
proposed, and runtime version output has not been collected.

After root selects that local tool identity, copy only the proposed `mix.exs`
and original `mix.lock` into a newly created private scratch project. Copy the
hash-bound installed Hex archive into a private Mix archive directory; do not
reuse global configs, caches, netrc, shared hosted dependency/build trees or
frozen identity dependencies. Run tool version checks, then:

```text
mix deps.unlock bandit jose
mix deps.get --only prod
HEX_OFFLINE=1 mix deps.get --only prod --check-locked
```

These are argv/env specifications in the plan, not shell commands executed by
this preparation. [Mix 1.20.4's documented single-dependency method](https://mix.hexdocs.pm/1.20.4/Mix.Tasks.Deps.Update.html)
keeps child locks when using unlock/get; `deps.update` also unlocks children and
recompiles, so it is excluded. The tagged
[unlock source](https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/mix/lib/mix/tasks/deps.unlock.ex)
drops the specified lock entries, and
[get source](https://raw.githubusercontent.com/elixir-lang/elixir/v1.20.4/lib/mix/lib/mix/tasks/deps.get.ex)
fetches through the dependency resolver. State paths use the official
[Mix environment controls](https://mix.hexdocs.pm/1.20.4/Mix.html#module-environment-variables);
private Hex state and bounded HTTP options follow
[Hex 2.5.1's config source](https://raw.githubusercontent.com/hexpm/hex/v2.5.1/lib/mix/tasks/hex.config.ex).
The `NETRC` override points to an absent private path as supported by its
[parser](https://raw.githubusercontent.com/hexpm/hex/v2.5.1/lib/hex/netrc/parser.ex).

Accept a generated lock only if the package set stays at 21, Bandit and JOSE
have the two selected versions, and all nineteen other complete lock entries
remain identical. Mix/Hex must generate and verify the checksum fields; neither
API metadata nor manual string substitution creates lock entries. Any required
extra change returns to root with the concrete resolver conflict and package
diff. A failed/incomplete resolution is evidence to retain, not permission to
unlock more packages, change tools or install another Hex.

Retain the actual lock, command logs, dependency inventory and custody receipt;
then remove only the marked scratch tree after all owned command groups are
absent. The plan does not compile/start product code, run tests, create a DB,
contact a provider or invoke OpenSSL. Mix necessarily evaluates its project
definition and may load dependency project metadata; this is dependency
resolution, not an OS sandbox.

## Existing narrow tests for a later upgraded graph

These source-selected methods already cover the application contracts. None was
run here. They are candidates for the unchanged full remote Phoenix CI or a
separately released focused host-test operation. The dependency-resolution
operation above does not include them. Do not invoke the local broad
callback/authority harness, which remains paused. Ordinary `mix test` also loads
`test/test_helper.exs`, so it cannot be treated as part of a dependency-only
operation.

| Existing source location | Contract already covered |
| --- | --- |
| `raw_webhook_capture_test.exs:185` | A 40,000-byte return exceeds the requested 32,768 bytes but stays accepted under the total cap; over-cap and declared-length excess reject. |
| `raw_webhook_capture_test.exs:198` | Inclusive 1 MiB body maximum, one-byte/empty/more/final and declared-length boundaries. |
| `raw_webhook_capture_test.exs:207` | No-progress and 64-read ceiling. |
| `customer_artifact_transport_test.exs:647,656,661` | Inclusive 6 MiB upload cap, one byte over, byte order, fixed deadline and finite read count. |
| `customer_workspace_transport_test.exs:482,497` | Nonempty body rejection even with declared zero; deadline and finite empty-more loops. |
| `access_token_verifier_test.exs:90,114` | Real 2048/4096-bit RS256 acceptance and altered/wrong/noncanonical signature rejection. |
| `access_token_verifier_test.exs:145` | Genuine RSA/HMAC/EC/EdDSA alternatives and `none` cannot widen RS256 policy; fallback and unsecured signing stay disabled. |
| `access_token_verifier_test.exs:501` | Whole-snapshot public-key policy rejects `d`, CRT and alternate key fields, merged private maps, weak keys, invalid exponent and wrong algorithm/use. |

The complete paths and hashes are in the preparation receipt. Byte-limit tests
use adapters; labeling one adapter HTTP/2 is not an actual Bandit wire receipt.
Existing real workspace/artifact integration tests construct HTTP/1 requests
and have DB/provider fixture dependencies; leave them to the unchanged remote
CI rather than replaying their local harness during this operation.

## Truly missing post-upgrade transport checks

Only two new focused host checks are proposed for later selection:

1. A bounded real HTTP/2 connection to a test-only loopback Bandit plug exercising
   the existing raw-capture reader across its 32 KiB requested read size and
   aggregate/declared byte limits. Verify exact accepted bytes and excess
   rejection with actual DATA framing/batching. Record the observed return sizes
   rather than assuming each read obeys `:length`. The fake-adapter over-target
   test already exists and needs no duplicate.
2. A bounded real HTTP/2 body read that receives WINDOW_UPDATE/SETTINGS frames
   without body progress. Verify the upgraded transport's one read deadline and
   owned stream/connection cleanup; use a small finite fixture budget and retain
   monotonic timing. Existing component tests exercise their supplied clocks or
   adapter results, not Bandit's non-progress frame loop.

No new JOSE application regression is required by the reviewed changes: the
existing methods already cover the reachable RS256/public-JWK contract.
WebSocket, JWE, ECDH and private-key export features remain outside this slice.
No new stress suite, local broad authority replay, production ingress proof,
native/device run or GA acceptance is selected. Root can deliver the coherent
upgraded slice and inspect the unchanged full remote Phoenix CI after its
separate dependency/validation selection.
