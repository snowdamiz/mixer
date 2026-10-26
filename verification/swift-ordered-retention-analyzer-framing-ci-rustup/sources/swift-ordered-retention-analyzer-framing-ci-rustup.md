# Framing CI rustup launcher repair

The framing runner now preserves the original `rustc` invocation path while
querying its sysroot, then hashes and invokes the actual `sysroot/bin/rustc`
compiler. It no longer classifies a rustup shim by its final symlink basename.
The CLI and existing macOS workflow selection are unchanged. The binding scope
remains `mixer-product-plan.md`; both acceptance flags remain false.

Delivered checkpoint `2e4ca9a347f9fe3ff8684b96672723886a7b9fad` failed this
step in Engine CI run `40244180264`. Its PATH launcher
`/Users/runner/.cargo/bin/rustc` resolved through Homebrew to
`/opt/homebrew/Cellar/rustup/1.29.0/bin/rustup-init`. The previous basename check
recognized only `rustup`, so it directly invoked the installer binary.
`rustup-init --version --verbose` returned exit 0 with a noncompiler identity;
the subsequent `--edition` invocation failed. **Zero Rust methods ran.**
The artifact upload succeeded and owned scratch was removed after children
returned. This was not a failed Rust behavior test or a 44-method CI pass.

The root-retained 57-member artifact is preserved as data under
`verification/swift-ordered-retention-analyzer-framing-ci-rustup/first-ci/`.
Its exact ZIP digest is
`165c0071c73c1fa5c9607a8d7995eabf1833578f3924f005c988806884fc82d3`.
The download receipt, original command logs and failure receipt are retained.
No artifact source was imported or executed.

The repair runs `[original_launcher, --print, sysroot]` in repository context
with `RUSTUP_AUTO_INSTALL=0`. Preserving the lexical launcher path preserves
rustup's `argv[0]` dispatch through both `rustup` and `rustup-init` shared-binary
chains. Missing installed toolchains fail rather than triggering installation.
The returned sysroot must be a single absolute path. Subsequent version and
compile commands invoke the resolved `sysroot/bin/rustc` directly. The receipt
records the launcher, resolved shared binary, actual compiler path/hash,
sysroot, verbose version and host. No install, update or toolchain configuration
command is issued.

Before compilation, the verbose identity must begin with `rustc`, identify
`binary: rustc`, provide a host and contain matching numeric release/header
versions. Exit 0 alone cannot admit an installer or manager. This is a compiler
identity sanity check with recorded executable hashes; it does not establish
cryptographic toolchain provenance or release authority. The command limits,
fixed selected sources, exact 44 names, failure retention, ownership cleanup
and unconditional acceptance refusals are unchanged.

Sixteen focused controls pass, including the original rustup case, a multihop
Homebrew-like default-PATH chain ending in `rustup-init`, installation disabled
during lookup, an exit-0 installer identity rejected before compilation, and
missing/inconsistent verbose identity fields. Existing compiler-failure,
inventory, output safety, timeout and cleanup controls remain exercised.
All 44 frozen Rust methods and their inputs remain byte-for-byte unchanged.

Local setup attempt 1 copied this Mac's 159-byte Homebrew shell wrapper rather
than its shared binary. Its sysroot query failed, zero Rust methods ran, and
the failure logs and owned-shim cleanup receipt are retained. Corrected setup
attempt 2 uses an owned copy of the actual Rustup 1.29.1 `libexec/bin/rustup`
binary, named `rustup-init`, behind the same two-symlink dispatch shape. The
runner CLI omits `--rustc` and selects that owned PATH launcher. The local
`RUSTUP_TOOLCHAIN=stable-aarch64-apple-darwin` selection is recorded, with
automatic installation disabled. This is a local fixture of the observed
dispatch shape, not a claim that remote Rustup 1.29.0 has passed.

That single selected execution passes all 44 methods on the actual Rust 1.99.0
`aarch64-apple-darwin` compiler, Python 3.14.8. Both runner scratch and the owned
shim tree are removed after their children return. All 894 original framing
members match their seals before and after; all 17 historical sidecars remain
invalid/failure 15. The unchanged test-only appended source still hashes to
`7d49836d83db32854172a0f399aa1b4fe9409b724c80abb4b531d8a930eb7747`.

The original 108-member handoff seal
`2175ba4d989c42261ae18352305e267c7dd3d7538fb5c8fdb844ea5a6f484ed6`
remains historical evidence for checkpoint `2e4ca9a`. Its four root source rows
are validated through that Git revision and their retained snapshots, rather
than compared with the repaired current files. The new packet preserves those
exact old sources and hash bindings. The original document and packet are
unchanged; the repair has its own source snapshots and seal.

Remote macOS qualification awaits root's review, push and actual CI inspection.
Linux remains unselected and unqualified because the frozen suite requires
Darwin layouts. No workflow, live VM, Cargo/dependency, hosted harness, authority
driver, rejected worker, broad harness, source preparer, CLI or target driver is
changed or executed. Computer use, capture, native runtime and phones remain
paused. Semantic, adapter/custody, target/native/device/signing/store/customer,
operations, published-package FieldLog and GA gates remain withheld. This lane
performs no commit or push.
