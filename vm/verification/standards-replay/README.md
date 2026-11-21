# Replay the pinned WebAssembly Core assertions

Run from the Mixer checkout on arm64 macOS with Xcode command-line tools,
Python 3.11 or later, and a local Rust toolchain. Use the Rust toolchain's
`bin` directory that contains both `cargo` and `rustc`.

```sh
python3 vm/verification/standards-replay/replay.py \
  --rust-bin "$HOME/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin" \
  --receipt verification/receipts/l03-standards-replay-local.json
```

The script resolves `HEAD` to a commit once, exports its entire `vm` tree into a
private directory under the local account's home, and verifies the archived files
against the committed Git blob IDs. It builds offline against that export with a
fresh Cargo home and `/` as Cargo's working directory. It refuses Cargo config
files in those lookup locations and workspace manifests above the export. Cargo
metadata must resolve the exported package and every target, including examples,
inside the verified tree. The script stages the release archive and exported public
headers in the experimental capability install layout, then links the exported
C client directly against that archive. It downloads the
pinned WABT release and five WebAssembly Core WAST files over HTTPS and checks
their SHA-256 hashes. [WABT release](https://github.com/WebAssembly/wabt/releases/tag/1.0.37) ·
[WebAssembly test sources](https://github.com/WebAssembly/spec/tree/05ca4182176763112561ae20153975c12bd689e4/test/core)

The script translates each WAST file and passes the selected Wasm bytes through
unchanged. It checks assertions against the upstream expected bits or trap and
requires the same outcome from the Rust CLI and the installed archive's
`mixer_vm_session_*_v1` C ABI for `mixer-table-memory-v3`. Each invocation starts
with a fresh instance, including each memory assertion. The client closes its
session after both returns and traps. For `assert_invalid` it checks the WABT
diagnostic and both Mixer validators' refusal codes. Mixer uses its default VM
and capability limits throughout.

`replay.py` lists the exact case selectors by WABT JSON line. For binary
`assert_invalid` commands, WABT can report the nested module's source line.
The selection covers integer wraparound, division and rotate, initialized
memory, sign and zero extension, exact f64 bits, the `meet-bottom` trap,
and invalid branch targets, stack types and memory bounds.

The same archive's `mixer_vm_capability_guest_ui_validate_v1` entry point checks
every selected module. The valid upstream modules lack the required Mixer
exports or defined memory. Guest UI V1 refuses them, so successful execution
evidence covers the shared V3 instruction profile through the V3 session ABI.
The selected invalid `load.wast` module declares memory and reaches the Guest
UI V1 body type check. This replay covers a fixed subset on the macOS host.
Stateful WAST sequences, Guest UI V1 application execution, and W08/L03 gate
qualification are outside its evidence.

The JSON receipt records the source revision, VM tree, Cargo targets, exact
fixture and module hashes, commands, assertion outcomes, and process custody.
The runner removes scratch after terminal custody and durable receipt
publication. A destination collision or publication error exits 74 and retains
scratch, including the command logs and a fallback receipt when it can be
written. Unknown process custody exits 74 and retains scratch and its
`HOLD.json` when the filesystem accepts the write. The runner prints the
retained path in either case.

Run the inert controls without downloading fixtures or compiling the VM.

```sh
python3 vm/verification/standards-replay/test_replay.py -v
```
