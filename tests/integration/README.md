# Local release integration

`release-workflow.py` starts the real Go development service on loopback in a
fresh temporary directory, uploads separately signed iOS/Android metadata and an
original integer Wasm fixture, validates/publishes local assignments, downloads
them through the public device endpoints, and invokes the Swift signature
verifier followed by the owned VM. It verifies replay/tamper rejection, retry
idempotency and actual integer results (50% and empty input). No private signing
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
