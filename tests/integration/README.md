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

`release-v2-workflow.py` builds the current service and a separate Swift package
using public `MixerUpdates` APIs. It exercises actual loopback HTTP for v1 and
v2, verifies signed payload/assignment bytes, reads v2's typed verified grants
and resource limits, and rejects replay and mismatched explicit versions. It
checks tenant authorization, route/key conflicts, failed-request preservation
of schema1, atomic upgrade to schema2, v1 byte preservation after restart and an
actual service binary built from commit6cb2759 refusing the upgraded snapshot.

```sh
DEVELOPER_DIR=/Applications/Xcode_26.6.app/Contents/Developer \
python3 -O tests/integration/release-v2-workflow.py \
  --swift /Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swift \
  --output-dir /absolute/new/evidence-directory
```

The output directory must be new. Commands use the bounded shared recorder and
a cleaned environment, record source/tool/binary hashes and preserve stdout,
stderr, request hashes and server lifecycle results. Checks remain active with
Python optimization. The explicit route version is never retried as another
version, and redirects/external artifact URLs are rejected. Fixture keys are
public TEST ONLY; bearer credentials are ephemeral and never written to logs.
Payloads are non-executable small strings. The Swift HTTP test consumer is
limited to small fixture payloads (96KiB) by metadata string bounds; it is not a
production large-payload downloader. Go service/PG payload limits have their
separate tests. No guest/native import, activation, physical device, OTA policy,
immutable published consumer adoption or hosted result is claimed.

Real PostgreSQL coexistence, RLS and commit/crash coverage is separate:

```sh
cd services
PATH=/opt/homebrew/opt/postgresql@17/bin:$PATH GOTOOLCHAIN=go1.26.4 \
python3 verification/postgres.py --output /absolute/new/postgres-evidence
```
