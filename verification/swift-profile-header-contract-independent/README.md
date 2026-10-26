# Independent initial profile/header contract review

Read `review.md` and `required-amendments.json`. The proposal needs five explicit
root amendments before dependent implementation selection: local layout versus
external build attestation, historical WASI pairing, before-first-attempt timing,
zero-byte ticket exclusivity and same-cache-owner row derivation.
`continuation-shape.md` gives the concrete cache-out-empty construction wrapper,
internal-only guard and guard-derived row bridge needed to close R3/R5 without
accepting a previously acquired cache, second snapshot or authority boolean.

`audit_inputs.py` independently verifies the assigned producer/root hashes, all
200 producer members/23,038,631 bytes,178 nested snapshots,132 archived/current
distribution members and131 reconstructed row source identities. It never
extracts, imports or executes archived code or reads another active lane.

`controls.py` contains48 independently authored offline methods, including
concrete positive/negative arithmetic/encoding cases and information-limit
counterexamples. Their synthetic Python values confer no Rust ownership,
compiled layout, real File custody, actual-header authority or runtime acceptance.
The producer's test scripts were read only, never imported or run.

Reproduce the bounded review with:

```
python3 -B verification/swift-profile-header-contract-independent/run_review.py
```

Each attempt gets a new `commands/runNNN` directory with exact argv, source input
identities, Python executable/version/hash, raw output, exit status and scope.
`seal.json` freezes the packet except its seal/sidecar. The original200-member
producer is unchanged. Root may advance unrelated repository HEAD; frozen hashes
remain authoritative. No product/native execution, UI/capture/process inventory,
Git mutation, dependency install or cap/deadline/crypto change occurs here.
