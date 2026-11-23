# Replay the authenticated FieldLog D6 build locally

Use Apple silicon, Xcode 27.2 (27B52), Rust 1.99.0 with the
`aarch64-apple-ios-sim` target, and Python 3.14. Supply local Git repositories for Mixer, FieldLog, Swift Crypto, and Swift ASN.1.
Populate the object stores and toolchains before running offline. The recipe
reads the pinned objects directly, including the FieldLog source tree.
[Source pins](prepare.py) · [Mixer](https://github.com/snowdamiz/mixer) ·
[FieldLog](https://github.com/snowdamiz/fieldlog) ·
[Swift Crypto](https://github.com/apple/swift-crypto) ·
[Swift ASN.1](https://github.com/apple/swift-asn1)

## Generate the unsigned worker input

Choose a new private directory under a real path. macOS `/tmp` is a symlink
and the worker's output-ancestry check rejects it. Run from the Mixer checkout.

```sh
recipe="$PWD/tests/integration/fieldlog-d6"
owner=$(mktemp -d /private/tmp/mixer-d6.XXXXXXXX)
work="$owner/replay"
rustc=$(rustup which rustc)

python3.14 -B "$recipe/prepare.py" --mixer "$PWD" \
  --fieldlog "$FIELDLOG_GIT" --crypto "$SWIFT_CRYPTO_GIT" --asn1 "$SWIFT_ASN1_GIT" \
  --rust-bin "${rustc%/*}" --output "$work"
python3.14 -B "$recipe/generate.py" "$work"
python3.14 -B "$recipe/build-guests.py" "$EMBEDDED_SWIFT_633_BIN" "$work/guests"
```

The source export uses stock CLI commit `78d25a1b8d` and the recorded FieldLog
and SDK deltas. The generator expects the accepted Debug project digest and
all 15 fallback-source hashes. The VM build must reproduce the pinned arm64
Simulator archive. The guest build compares each module to its historical
length and prefix hash. The run signs the full fresh module bytes, including
the 16 trailing data bytes that can differ.

## Build, download, and publish on loopback

Put PostgreSQL 17 and the Erlang and Elixir versions from
`$work/hosted/.tool-versions` on `PATH`. Seed `$work/hex` and `$work/mix`
from local Hex package caches for the pinned `hosted/mix.lock`. Use OpenSSL 3
on `PATH` for disposable Ed25519 fixture keys. Compile the pinned Phoenix
tree in place. Keep the CLI and its SwiftPM resource bundles together.
Use the stock worker package policy with the pinned local dependencies.
The initial outer sandbox stopped the SwiftUI macro plug-in.

```sh
(
  cd "$work/hosted"
  export HOME="$work/home" HEX_HOME="$work/hex" MIX_HOME="$work/mix"
  export TMPDIR="$work/tmp" MIX_ENV=test HEX_OFFLINE=1 ERL_FLAGS='+S 4:4'
  export GIT_ALLOW_PROTOCOL=file
  mix deps.get --only test
  mix compile
)
python3.14 -B "$recipe/managed.py" "$work"
python3.14 -B "$recipe/renew.py" "$work"
python3.14 -B "$recipe/release-host.py" "$work"
```

Reserve loopback port 54811 for the release lease. The build lease creates
one authenticated build via the stock browser API. The restricted Oban
processor dispatches the pinned worker. The receipt must show create 201,
owner detail and download 200, outsider detail and download 404, and
anonymous download 401. Compare the exact MXNATIVE1 body with the retained
object, descriptor, and native journal for the same attempt.

Run renewal after worker and listener closure. Renewal reopens the HTTP
attachment, hashes its Mach-O and resources, and binds a new runtime to the
archive, worker binding, lock, projected source, and VM. It writes only new
trust roots and the matching identity into the private app copy. It verifies
each Ed25519 signature and removes the private keys before publication. The
separate Phoenix lease uses the stock CLI to publish twice and roll back.
Check journal sequences 1, 2, and 3 and empty offers for both prior runtime
fingerprints.

## Hand off the exact product for native replay

Give root the same-attempt owner and seal receipts, the renewed app, and
[D6ReleaseObserver.swift](D6ReleaseObserver.swift). Build its XCTest runner
from the pinned FieldLog Xcode project's existing `FieldLogUITests` target
using the public checkout. Replace the `FieldLogUITests.swift` input with the
observer for this disposable build. Use the generic Simulator destination
with signing disabled. Root substitutes the renewed owner app for the
observer build's app. Root owns ad hoc signing, strict signature readback,
the owned Simulator UUID, and the native controller.

Compare non-signature Mach-O bytes across signing and keep stable app
resources byte-for-byte. Run the selector
`FieldLogUITests/D6ReleaseObserver/testBaselineReviewRollbackAndOffline`.
The controller supplies the same `D6_WORKSPACE`, `D6_CONTROL`, and `D6_TICKET`
to the observer across phases. Publish baseline before the first launch,
publish review and rollback on the observer's phase transitions, and stop
the release origin before offline cold reopen. Verify the visible sequence,
activation journal, installation and workspace hashes, and group, port, and
device cleanup under the repository's native ownership rules.

The historical installed pass is pinned in Mixer commit
`7ece7052e722e8031fb0cf98d57891adb47585b6` under
`verification/receipts/l08-d6-exact-authenticated-download-native-20261123.json`.
Independent review was `l08-d6-exact-authenticated-native-closure-b52f5d2380`.
A fresh Mach-O can differ from the historical download, even with the same
generator project. Use SHA-256 and UUID from the current worker/download
pair, then verify the runtime and signatures for that pair. Preserve the
historical SHA-256 as evidence of the prior attempt.

After terminal custody and port closure, delete the owned replay directory
and retain compact receipts only. Preserve any namespace reported under a
custody hold.
