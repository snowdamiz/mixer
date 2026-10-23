# Proposal evidence only

`docs/swift-reactor-owned-profile-design.md` proposes an additive Rust-only exact
reactor admission/composition boundary. Root approval is pending. No profile,
validator, cache, execution or adapter source is changed by this follow-up.

Run `python3 -B verification/swift-reactor-profile-design/collect.py` to bind its
inputs. The collector independently hashes the retained exact target, checks
existing final diagnostic/descriptors agree on counts and artifact identity,
records source hashes/revision/tool/command and computes the stated byte/control
arithmetic. `proposal-inputs.json` and `collect.stdout` contain the observed
result. This does not type-validate, decode or execute the reactor, and its
`valid=false`, `authorization=false` flags remain deliberate.

All proposed ceilings and the private composition/API ownership changes require
root acceptance before implementation. Dynamic fuel, work, recursion, cache
pressure, live values/controls and peak reservation requirements remain unknown.
There are no downloads, external fixtures, device queries, package publications,
production actions or GA gate approvals in this evidence.
