# Local release integration

`release-workflow.py` starts the real Go development service on loopback in a
fresh temporary directory, uploads separately signed iOS/Android metadata and an
original integer Wasm fixture, validates/publishes local assignments, downloads
them through the public device endpoints, and invokes the CLI's linked Swift
signature verifier followed by the owned VM. It verifies replay/tamper rejection,
tenant authorization, retry idempotency/conflict detection, a signed memory ceiling,
and actual integer results (50% and empty input). No private signing
keys are written; the temporary publisher token and service state are removed.

Run from the repository with Swift 6.2+, Rust and Go 1.26 available:

```sh
swift build --package-path cli
swift build --package-path updates
cargo build --release --manifest-path vm/Cargo.toml
python3 tests/integration/release-workflow.py
```

Both platform scopes run on the current development host. This is a local
integration receipt, not device OTA activation, full Swift execution, hosted
PostgreSQL durability, compiler eligibility, policy approval or publication.
The payload is a small independently authored integration fixture, not FieldLog
or a substitute for its native/guest qualification corpus.

The CLI links `MixerUpdates.ReleaseVerifier`; external tool success cannot replace
signature verification. The CLI snapshots opened regular input files, checks
strict structured tool receipts, and passes signed fuel/memory ceilings to the VM.
The integration freezes local executable copies, ignores ambient `MIXER_VM` and
`MIXER_UPDATE_TOOL` overrides, records executable/harness SHA256 and command results,
disables HTTP redirects, and uses checks that remain enabled under Python `-O`.
Command output is bounded and streamed rather than captured in unbounded pipes.

The CLI supports explicit local tool overrides for developer diagnostics. Those
executables are trusted local code: a malicious script could forge a valid-looking
VM receipt. Tool hashes identify observed bytes and detect ordinary replacement;
they do not sandbox local code or attest that an existing binary was built from
the current source tree. This developer path does not authorize device updates.
