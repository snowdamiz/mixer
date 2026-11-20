# Rebuild the signed Android selected-draft packet

This L08 §22.2.4 development fixture rebuilds FieldLog's ordinary Android
editor and signed checklist from Git inputs. The Android source profile is
Pair24, because it supplied the reviewed selected-draft binding. The public
Mixer base is `d82b78782ae1a9bcccdbc2e3d5890a78ba27413c`. The build uses its
pinned ancestor `5dea19db36610e312b51918b384364ba590b6ef8` and FieldLog
`552559d2d3278abb9b1aa7dcf0288102c09a202b`. The recipe checks the applied
FieldLog tree and the renderer, binding, VM, and package input digests.

## Build and replay on macOS

Use arm64 macOS, Python 3.14, Xcode 27.2 (27B52) at
`/Applications/Xcode.app`, and Xcode 26.6 (17F113) with the macOS 26.5 SDK at
`/Applications/Xcode_26.6.app`. The recipe uses Swift 6.3.3 with the Android 28
and embedded Wasm tools, Android NDK 27.1.12297006, Android platform 37.0,
Build Tools 36.0.0 and 37.0.0, JDK 25.0.4.1, and Rust 1.99.0 with
`aarch64-linux-android` and the matching `llvm-tools` component. See the
[tool paths](recipe/environment.zsh).

Install the Rust toolchain and verify the host `llvm-nm` that the pinned VM
builder uses to inspect both archives.

```sh
rustup toolchain install 1.99.0 --profile minimal
rustup target add --toolchain 1.99.0 aarch64-linux-android
rustup component add --toolchain 1.99.0 llvm-tools
export RUSTUP_TOOLCHAIN=1.99.0
rust_sysroot=$(rustup run 1.99.0 rustc --print sysroot)
test -x "$rust_sysroot/lib/rustlib/aarch64-apple-darwin/bin/llvm-nm"
"$rust_sysroot/lib/rustlib/aarch64-apple-darwin/bin/llvm-nm" --version
```

Place the pinned Swift Crypto 5.0.3 and Swift ASN.1 1.7.3 Git mirrors at the
paths in [`recipe/offline-swiftpm.zsh`](recipe/offline-swiftpm.zsh). The build
checks their tag commits before using them.

Use an authenticated GitHub CLI to read the pinned FieldLog commit, or set
`FIELDLOG_PINNED_GIT_REPOSITORY` to a local Git repository containing it.
Run the maintained recipe from the Mixer checkout root with a fresh output
directory. The checkout must contain the pinned public base and its build
ancestor. The recipe builds DEX, both Wasm guests, and JNI from source.

```sh
recipe="$PWD/tests/integration/fieldlog-saved-draft/android"
mkdir -p "$PWD/verification/local"
scratch=$(mktemp -d "$PWD/verification/local/fieldlog-android-source.XXXXXXXX")
python3 -B "$recipe/run-owned.py" "$scratch/custody.json" 1800 "$scratch/rebuild" -- \
  /bin/zsh -f "$recipe/rebuild.zsh" "$PWD" "$scratch/rebuild"
```

The wrapper records the outer command exit and process-group absence. It
requires FieldLog's create command record in
`rebuild/work/prepared/.fieldlog-build/commands.json`, the pinned Mixer's
create tool receipts under `rebuild/work/tmp/`, and the pinned VM builder's
completion receipts in `rebuild/work/{android,host}-engine/receipt.json`.
The VM builder writes its completion receipt after the captured commands
close. The wrapper checks the seven Android and nine host command records
and records the receipt and archive digests.

If any expected terminal record is missing or unresolved, the wrapper reports
`UNKNOWN` and exits 74, even after the outer command exits zero. Preserve the
entire attempt directory and use `custody.json` to identify the unresolved
evidence. Treat a missing or unreadable `custody.json` as `UNKNOWN`. Compiler
and test logs are in `rebuild/work/logs/`.

A successful run writes an APK, the four signed assignments, fresh Wasm, the
loopback origin, and `rebuild-receipt.json` under `rebuild/packet/`. Verify
`SHA256SUMS` there before handing the packet off. Keep the packet with
`custody.json`. Remove the owned `rebuild/work/` only after the wrapper
records `terminalCustody: TERMINAL` and you collect the evidence. The APK
passes Android v3 signature, 16 KiB ZIP
alignment, and JNI ELF alignment checks. Each run uses fresh development keys.
Wasm bytes can vary across identical source builds. The recipe validates the
fresh modules before sealing and checks the exact bytes and signed digests
afterward. The reviewed startup and resource limits and 50 ms VM turn remain
enforced.

## Interpret the recorded timings

The historical receipt pins the sealed packet and the recipe manifest used to
build it. It records one clean rebuild on the development host. Its 50 ms
process sampling interval could miss short-lived groups or groups that changed
parent between observations. Earlier samples started late or after the command
finished, as recorded per attempt. Use the command receipts for custody.
[Historical rebuild receipt](../../../../verification/receipts/fieldlog-android-saved-draft-terminal-d82b7878.json)

The rebuild duration and press and first-frame traces are individual
development observations. One earlier host replay hit the 50 ms VM turn
timeout. Android input latency and first-draw timing require measurements on
the installed Android app.

Run the custody controls on the host with Python and inert subprocesses.

```sh
python3 -B tests/integration/fieldlog-saved-draft/android/test_run_owned.py -v
```

## Use a fresh Android installation

All four assignments share the new APK's embedded runtime and public trust
root, beta channel, and FieldLog Android development scope. Use the same
installation and workspace for sequences 1 (baseline), 2 (optional), 3
(rollback), and 4 (re-upgrade). The packet's host installation UUID identifies
the macOS proof. Root records the newly created Android installation ID and
repins the device runner to the SHA-256 of `rebuild-receipt.json`. The former
APK and its installation are separate and remain under root custody.

On macOS, the host presentation transport uses the public Mixer witness API
and runs the signed packet against the
same FieldLog repository actor through all four assignments. It verifies first
frame and the action result, one extra read for baseline and rollback, one
optional write followed by a read, stable JPEG bytes and outbox, isolation of
the unselected draft, denial of the unselected key and retired lease, an
ordinary offline save, and cached rollback. It reads the saved note and true
flag from disk before the re-upgrade, then reopens the repository to verify the
same note and false flag. The receipt also records APK and delivery verification
and retirement of the host presentation owners. Android Java callbacks and
first draw still require installed replay.
