# Replay signed FieldLog D8 F02 on macOS

Run from the Mixer checkout containing this directory. Use Xcode 27.2, Swift 6.3.3 Embedded Swift, Rust with the locked dependencies cached, and SwiftPM's local swift-crypto and swift-asn1 Git caches. Point `stage` at the Mixer source pin, `fieldlog` at a Git repository with the two historical commits, and `packet` at the sealed F10 three-release packet.

```bash
set -euo pipefail
umask 077
stage=/absolute/path/to/mixer-stage
fieldlog=/absolute/path/to/fieldlog
packet=/absolute/path/to/f10/packet
recipe="$PWD/tests/integration/fieldlog-d8-f02-signed"
pin=362d64844e9c25fe0526177b138251e8705fa2ea
before=1587d2d4f02ab2dad9914df97f878727dd622296
after=32c063e748e48db391e878890edeb247a71d08d9
mkdir -p verification/local
work=$(mktemp -d "$PWD/verification/local/f02-signed.XXXXXXXX")
mkdir "$work"/{source,lib,guest,tmp}
export TMPDIR="$work/tmp" SWIFTCI_USE_LOCAL_DEPS=1
export SWIFTPM_MODULECACHE_OVERRIDE="$work/modules" CARGO_INCREMENTAL=0
export CARGO_PROFILE_RELEASE_DEBUG=0
export PATH="$HOME/.rustup/toolchains/stable-aarch64-apple-darwin/bin:$PATH"

git -C "$stage" archive "$pin" vm sdk updates capability-activation runtime-identity \
	experimental-capability-runtime | tar -xf - -C "$work/source"
for name in swift-crypto swift-asn1; do
	version=$(jq -r --arg name "$name" '.pins[] | select(.identity == $name) | .state.revision' \
		"$work/source/sdk/Package.resolved")
	cache=("$HOME/Library/Caches/org.swift.swiftpm/repositories/$name-"*)
	test "${#cache[@]}" = 1
	mkdir "$work/source/$name"
	git --git-dir="${cache[0]}" archive "$version" | tar -xf - -C "$work/source/$name"
done
sed -i '' 's|.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")|.package(path: "../swift-crypto")|' \
	"$work/source/sdk/Package.swift" "$work/source/updates/Package.swift"
package="$work/source/capability-activation"
for source in FieldLogModels/Workspace.swift FieldLogStorage/WorkspaceRepository.swift; do
	test "$(git -C "$fieldlog" rev-parse "$before:Sources/$source")" = \
		"$(git -C "$fieldlog" rev-parse "$after:Sources/$source")"
	mkdir -p "$package/Sources/$(dirname "$source")"
	git -C "$fieldlog" show "$after:Sources/$source" > "$package/Sources/$source"
done
mkdir "$package/Sources/F02Control"
cp "$recipe"/{Control,Release,Storage}.swift "$package/Sources/F02Control/"
cat >> "$package/Package.swift" <<'SWIFT'
package.targets.append(contentsOf: [
    .target(name: "FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"]),
    .executableTarget(name: "F02Control", dependencies: [
        "MixerCapabilityActivation", "FieldLogModels", "FieldLogStorage",
        .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
        .product(name: "MixerUpdates", package: "updates"),
        .product(name: "MixerCapabilities", package: "sdk"),
        .product(name: "MixerGuest", package: "sdk"),
        .product(name: "MixerUI", package: "sdk"),
    ]),
])
SWIFT
cargo build --offline --locked --release --lib --features experimental-capability-native \
	--manifest-path "$work/source/vm/Cargo.toml" --target-dir "$work/rust"
vm="$work/rust/release/libmixer_vm.a"
ln -s "$vm" "$work/lib/libmixer_vm_capability_experimental.a"
swift build --package-path "$package" --scratch-path "$work/swift" --cache-path "$work/cache" \
	--config-path "$work/config" --security-path "$work/security" --jobs 8 -Xswiftc -gnone \
	-Xcc "-I$work/source/vm/include" -Xlinker "-L$work/lib" --product F02Control
host="$work/swift/out/Products/Debug/F02Control"

suite=tests/integration
git -C "$stage" show "$pin:$suite/fieldlog-task-calculation/guest/TaskWire.swift" |
	sed 's/let rowCount = 3/let rowCount = 2/' > "$work/guest/TaskWire.swift"
git -C "$stage" show "$pin:$suite/fieldlog-saved-draft/guest/CapabilityImports.c" > "$work/guest/CapabilityImports.c"
wasm="$HOME/Library/Developer/Toolchains/swift-6.3.3-RELEASE.xctoolchain/usr/bin"
(
	cd "$work/guest"
	"$wasm/clang" --target=wasm32-unknown-none -ffreestanding -Oz -c CapabilityImports.c -o capability.o
	for variant in prior exact; do
		define=FIELDLOG_BASELINE
		if [[ "$variant" == exact ]]; then define=FIELDLOG_UPDATED; fi
		"$wasm/swiftc" -target wasm32-unknown-none-wasm -enable-experimental-feature Embedded \
			-enable-experimental-feature Extern -whole-module-optimization -Osize -parse-as-library \
			-Xfrontend -disable-stack-protector -D "$define" -module-cache-path modules \
			-emit-object "$recipe/Guest.swift" TaskWire.swift -o "$variant.o"
		"$wasm/wasm-ld" --no-entry --gc-sections --strip-all -z stack-size=16384 --max-memory=65536 \
			--export=mixer_guest_ui_start_v1 --export=mixer_guest_ui_hydrate_v1 \
			--export=mixer_guest_ui_event_v1 --export=mixer_guest_capability_ready_v1 \
			"$variant.o" capability.o -o "$variant.wasm"
	done
)
(cd "$packet" && shasum -a 256 -c MEMBERS.sha256)
python3 -B "$recipe/journey.py" "$host" "$package/Tests/MixerCapabilityActivationTests/Fixtures" \
	"$work/guest" "$vm" "$packet/tools/stock-mixer-service" "$packet/tools/mixer" "$work/run"
jq '{status, phases, originCleanup, hold}' "$work/run/receipt.json"
```

The run records revisions 3, 4, 5, 5, and 5 across five host processes. After
you retain the receipt and logs, remove the owned scratch if custody is terminal.
The receipt includes the origin publication audit and the offline workspace digest.
