# Frozen experimental VM archive builder

`../build-vm.py` is a separate local developer builder for the experimental
capability Swift package. It does not modify the legacy builder, select an OTA
release, validate an identity fingerprint, or qualify a device.

Run with Python 3.11 or newer, Git, an installed official Rust toolchain with its
`llvm-tools` component, and the requested Rust standard-library target. On Apple
platforms, Xcode command-line tools/SDKs are required. Android requires the
installed official NDK. The builder does not install or download any tools.

```sh
python3 experimental-capability-runtime/build-vm.py \
  --revision b25e3b7de2391a80d12e7fd75e60903495bec120 \
  --target host \
  --output /absolute/fresh/output \
  --rustc /absolute/path/to/rustc
```

`--rustc` is optional when `rustc` is discoverable on the incoming `PATH`. It may
name an installed rustup selector. The selected sysroot's actual Cargo, rustc and
matching LLVM `llvm-nm` are used and hashed; the build environment uses that
sysroot plus system tool directories. User Cargo configuration, wrappers,
`RUSTFLAGS` and dependency caches are not inherited. The private working directory
for commands is `/`, with root Cargo configuration rejected. `HOME` retains its
normal meaning. An explicit `DEVELOPER_DIR` and `RUSTUP_HOME` may select installed
official tools. Android's documented linker/page-size flags are set explicitly.
Tool binaries and SDK contents are trusted installed inputs; this does not attest
their distribution or freeze their complete transitive contents.

Choose `host`, `ios` (arm64 iOS17), `ios-simulator` (arm64 iOS17 simulator), or
`android` (arm64 API28, NDK `--ndk /absolute/ndk-root`). Apple host deployment is
macOS14. Each output must be a fresh absolute path. The builder never removes,
reuses or overwrites an existing output. It writes a regular-only `source.tar`,
the same frozen regular Git blobs under `source/`, a complete source hash manifest,
command logs, and finally `receipt.json`. A failed attempt can retain partial
files and `failure.json`; its absence of `receipt.json` means incomplete.

Successful staging contains exactly:

- `lib/libmixer_vm_capability_experimental.a`
- `include/mixer_vm_capability.h`
- `include/mixer_vm.h`

The archive contains both C families and one shared registry. Compile Swift using
`-Xcc -I<output>/include` and link only `-L<output>/lib` plus the distinct library
name `mixer_vm_capability_experimental`. Never add a Cargo directory to Swift's
library search path, co-link the default Rust archive, or compose this experimental
package with the normal `MixerRuntime` product in this slice.

Only a complete lowercase forty-hex commit object is accepted. Dirty working-tree
files and moving refs are not build inputs. Required headers and transport bytes
must match the reviewed constants; the legacy header copies must agree. The
explicit native-to-guest-to-mailbox feature chain, empty defaults, static target,
absence of dependencies/build scripts and standard library source path are checked
before creating output. Cargo then runs `build --locked --offline --release --lib
--no-default-features --features experimental-capability-native`. These checks are
ordinary branches and remain active under `python -O`.

Without `--cache`, Cargo's cache is private to the new output. For local reuse,
`--cache /absolute/owned/cache` must be separate from the output (neither may contain
the other). The selected cache is an explicitly trusted, coordinated developer
resource: it must be owned by this user, have no group/other write permissions,
contain regular files/directories only, and have no external hardlinks. Cargo's
hardlinks wholly inside the cache are allowed after counting all inode references.
An advisory exclusive lock coordinates *this builder*; other Cargo invocations do
not honor it and must not use the cache concurrently. No hostile same-user race
sandbox, arbitrary compiler sandbox, or general filesystem write-confinement claim
is made. Descriptor-relative no-follow exclusive output creation prevents reuse of
preexisting symlinks/hardlinks; source and output identity are checked around the
build. The trusted compiler is still given ordinary filesystem paths.

Every bounded command runs in a private process session. Timeout, output overflow,
nonzero exit or a successful parent leaving descendants triggers whole-group kill
and parent join, followed by bounded group-exit observation. Exceptional cleanup uses the same group-exit observation. A group that remains
present is an explicit cleanup failure and quarantines a held cache with a sticky
marker. KeyboardInterrupt or SystemExit while a cache is held conservatively
quarantines it even when group cleanup succeeds; no interrupted artifact is staged
as complete. This cannot contain a hostile tool that deliberately escapes its session,
or promise a wall-clock bound on kernel-level uninterruptible termination. No
quarantined cache is automatically cleared or reused.

Receipts record committed source/blob/archive/header hashes, builder hash, exact
commands/log hashes, selected tool/compiler identities and target, and the staged
archive bytes. Build elapsed times are development observations. No bit-for-bit
binary reproducibility, release authorization, signed attestation, full Swift
execution, native I/O, identity embedding, publication or device result is claimed.
The source export is self-contained for this dependency-free VM build and contains
its contract/schema inputs; no mutable SDK checkout is consumed.

Run original boundary probes with:

```sh
python3 experimental-capability-runtime/build-tests/test_builder.py
python3 -O experimental-capability-runtime/build-tests/test_builder.py
```

Those temporary Git fixtures probe input and filesystem policy, not native VM
semantics. Actual pinned host/C and cross-link evidence is recorded separately by
`run.py`. `local/` contains retained large source exports, static archives, binaries
and incomplete experiments and is ignored by Git. Checked-in logs/receipts retain
hashes and scope, without embedding large generated binaries.
