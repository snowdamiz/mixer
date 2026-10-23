# Identity v2 host qualification

This slice implements the explicit `CapabilityRuntimeIdentity` parser, CLI
`inspect-v2`, v2-only declared-input capture/verification and v2 source emitter.
It implements no release verifier, installed adapter factory, activation or native
capability execution. Authoring model: gpt-6.1-sol, xhigh.

The frozen candidate contains21 runtime-identity source/data files. Their exact
hashes are in `candidate-inputs-v2.json` (SHA-256
`2e390da57743c56960e8f449f3fe037bd3d3bad459638e548562be4f1c547433`);
the sorted source map digest is
`322e54c775a051911b845df3b7e26cd3b12ed9e83e2f3d6e308a362e881a3d84`.
The final driver is `run.py`, SHA-256
`b0d6ac1fac086ed2804721a2cf6e513dd2afcbe5e42fd847ab63c6874b912f74`.
No contract, header, VM, SDK, release or service source was changed.

The runner exports these owned files and immutable dependencies from
`aca686bfc72b8f18db727de5307977fb51790e0a`, preserving the existing direction
`runtime-identity -> updates`. Concurrent new release-v3 source is deliberately
excluded. The final export map digest is
`b32e4e9b2b425e2ea5b535f01f3f37ecccef177011a87baece1f06ba5f884755`.
The export includes the exact frozen contracts/headers/schema and the legacy
activation test descriptor. It neither edits nor relies on a mutable SDK checkout.
The SDK semantic preimages used in tests are reconstructed from the frozen schema;
remaining build artifacts/native inputs are explicitly original synthetic data.

The final receipt is `2026-10-23-final-v2-snapshot/receipt.json`, SHA-256
`cf7d181c73bae75fda56799072c289e5b7811f8d76032336a1aee025bb2412fb`.
Its companion `seal.json`, SHA-256
`036b1070b96a6aab494ff59ca3f828e2ef62d3e8608768618e333d5c94b2763a`,
records all45 retained evidence files, including nested consumer receipts. The
receipt records27 successful outer commands, source hashes, actual tool versions,
CLI binary hash, outputs and development elapsed times. Timing is not a product
performance claim; no bit-reproducibility claim is made.

Observed host results:

- 19 Swift test functions passed in debug and release:8 unchanged v1 and11 v2.
- 32 Python test functions passed normally and under `-O`:19 legacy and13 v2.
- Seven v1 and11 v2 independently authored Python restricted-CBOR/hash vectors
  matched Swift. Schema2 is domain-separated from schema1 and all release domains.
- All seven valid legacy CLI vector outputs matched a separately built committed
  v1 CLI byte for byte. Ten existing v1 parser/test/fixture/tool/manifest files
  remained byte-identical. The CLI and two READMEs changed additively.
- Two real generated-v2 Swift consumers ran after deletion of their input
  snapshots/original files, recovered protocol3/ABI2/route and rejected a changed
  embedded fingerprint with exit3. Exact generated source, main program, package,
  commands and outputs are retained per Python mode. These are host executables,
  not signed apps or device receipts.

New tests cover every descriptor leaf, closed fields and lexical JSON ambiguity,
exact contract/header/schema binding, version/domain/downgrade rejection, platform
binding, sorted capability records, narrow exact/+1 ceilings, zero-page downward
conversion and owned snapshots. Capture tests exercise actual copied native
preimages, material family/schema/concurrency checks, canonical bytes and bounds,
missing/extra/collection-role rejection, empty-native rejection, malformed
5000-digit numeric input, mutation during a pinned read, symlink/external-file
safety, snapshot corruption, failed-sync atomic cleanup, existing-output safety,
explicit v2 CLI and optimized-Python guards. No copied digest creates native
adapter authority, and empty installed grants remain denials.

Replay from the repository root with fresh output and official Swift/Python:

```sh
python3 verification/runtime-identity-v2/run.py \
  --output /absolute/private/fresh-identity2-qualification --swift /usr/bin/swift
```

The retained initial exploratory Python failure under `development/` resulted
from the concurrently authored, then-uncompilable `updates/VerifierV3.swift`,
not a frozen v2 identity result. That development run is not claimed as an
immutable source qualification. `development/first-driver.py` preserves the
first passing matrix driver before adding the separate v1 CLI control. Final
source and all final logs are frozen independently above. Local exports/builds
under `local/` are replay aids and are not the committed evidence bundle.

The `InstalledRuntime` projection is a raw immutable DTO; the old verifier rejects
its protocol3/ABI2 tuple. Neither parser nor capture proves compiler version
truth, full dependency graph, actual build consumption, final binary identity,
linked SDK implementation, complete installed material factory, payload admission,
signed v3 authority, native effects, actual health, full Swift/UI/FieldLog,
published packages or GA. Complete adapter/activation composition, integrated
release-v3 replay and physical lifecycle qualification remain separate work.
Phones were not accessed.

## Snapshot correction and superseded evidence

Root review found that the initial v2 parser let StrictJSON scan `Array(data)`
and then decode the caller's original Data, which can wrap externally mutable
no-copy storage. The parser now checks the128KiB limit before making an explicit
owned `Data(bytes:count:)` copy. Scanner, decoder, validation and canonicalization
all use that snapshot. The correction changes only the new v2 parser/test.

`snapshot-fix/receipt.json` SHA-256
`6286d2948b197dbc3b05b45bc451bc7432a2b964bc35f557f80cf3d20cd218b8`
records a deterministic test-only scanner boundary hook in two private dependency
exports. The old parser accepted an unscanned duplicate-key replacement with
fuel777777; the fixed parser retained its scanned owned snapshot with fuel1000000.
Both reject that duplicate input when scanned normally. The hook/test/logs and
source hashes are retained there; no production hook or StrictJSON/v1 edit exists.
This proves consistent owned bytes across validation passes, not an atomic view
of a concurrently modified external buffer while the initial copy is collected.

`candidate-inputs.json` and `2026-10-23-final/` remain unchanged historical evidence
for the superseded initial parser. They are not the current candidate. The new
manifest and `2026-10-23-final-v2-snapshot/` are the current qualification above.

The original `snapshot-fix/reproduce.py` and its receipt stay unchanged as the
executed historical attempt. For a fresh clone, use the added portable helper:

```sh
python3 verification/runtime-identity-v2/snapshot-fix/portable-replay.py \
  --output /absolute/private/fresh-snapshot-boundary
```

It checks `candidate-inputs-v2.json`, exports frozen dependency bytes directly
from Git `aca686b`, and uses the retained exact old parser fixture
`OldCapabilityRuntimeIdentity.swift.txt` (SHA-256 `8fe3feae4f1e7d1e114c60c860b9f9a423cfdc0e8f88779d1f519edb286738c6`).
It needs no ignored historical source tree. The portable helper SHA-256 is
`d18b4dcb068fb51ec538f77142daa38125348588f0d38178f23d22714beeab0b`;
its argument parsing/help was checked, but the existing two compiled boundary
runs above were not repeated for this portability-only addition.
