# UP5 iOS shared Text and Button

Create `MixerNativeTheme(configuration:)` once from the app's validated shared
V2 descriptor and pass the value to `MixerNativeView.sharedTheme` and
`MixerGuestScreen.sharedTheme`. The guest screen retains its existing native
attachment and action handler. The selection belongs to the app shell. A
theme contains no installed resource, signed release, or display receipt.

| Input | iOS mapping |
| --- | --- |
| Descriptor | One shared V2 theme with system sans and an empty resource catalog. The full descriptor codec validates before the binding is created. |
| Light and dark | SwiftUI `colorScheme` selects the V2 light or dark palette. |
| Literal Text | Body, headline, title, and caption use the corresponding foreground and measured type role. The renderer retains the node's line cap, selection, and accessibility modifiers. |
| Literal Button | Normal, destructive, and cancel use the corresponding V2 role paints. Native `ButtonStyleConfiguration.isPressed` selects pressed paint when enabled. Inherited `isEnabled` takes precedence and selects disabled paint. V2 logical label insets, minimum hit size, and corner radius use 1/64-point units. SwiftUI Button owns activation, role, and accessibility. |
| Dynamic Type and Bold Text | The 12 SwiftUI sizes map directly onto the 12 measured V2 profiles. An unknown category uses the descriptor's default profile. SwiftUI bold legibility selects semibold for regular/medium and bold for semibold/bold at the same point size. |
| Increased Contrast | SwiftUI increased contrast selects opaque black-on-white in light and white-on-black in dark for these leaves. Each leaf paints its own backdrop because enclosing collection or app surfaces may have another appearance. The button uses a two-tone edge and an inner stroke that is thicker when pressed and dashed when disabled. |

TextField, Toggle, navigation and section titles, lists, containers, app
canvas, focus outline tokens, bundled assets, and platform-specific
descriptors are outside this binding. The private UIKit renderer keeps its
previous resolver entry point and Bold Text and increased-contrast refusal.
Omitting the binding keeps the existing native Text and Button appearance.

## Build-only proof and source controls

Run from a clean arm64 checkout with Xcode 27.2 and Ruby xcodeproj. Build
for a generic Simulator destination with the iOS 17.0 deployment target.
The fixture uses the arm64 Simulator VM and four headers pinned in
`prepare.py`. The accepted VM library is the one in the S4 recovery
successor. Its builder and exact source are reproducible with the following
command (Rust 1.99.0 with llvm-tools and the Simulator target). A different
binary digest requires a deliberate fixture pin update.

```sh
mkdir -p verification/local
base=$(mktemp -d "$PWD/verification/local/up5-theme-build.XXXXXXXX")
mkdir "$base/build" "$base/host"
revision=$(git rev-parse HEAD)
fixture=capability-activation/verification/up5-ios-shared-theme
python3 -B experimental-capability-runtime/build-vm.py \
  --revision 692f05cd2d31f218ae9b3cef7253a4e7397f8e17 \
  --target ios-simulator --rustc "$UP5_RUSTC" --output "$base/engine"
sh "$fixture/build.sh" "$base/build" "$base/engine" "$revision" > "$base/build.log" 2>&1
sh "$fixture/check-source.sh" "$base/host" > "$base/source.log" 2>&1
```

The host command executes the real appearance mapping with the independent
fixture inputs. It checks all three roles and native state precedence, light
and dark, the contrast legibility choices, descriptor rejection, and the
legacy resolver's refusal. Its outputs scope to source behavior.

## Root Simulator replay

Run `UP5ThemeUITests/UP5ThemeUITests/testProductThemeOnBundledAndSignedGuest`
only on an exact, root-owned, already booted iOS 26.5 Simulator after the
Accessibility preflight. Supply a fresh root evidence directory. Root
owns the device baseline, cleanup, and result interpretation.

```sh
OWNED_SIMULATOR_UDID="$owned_uuid" UP5_ROOT_EVIDENCE="$root_evidence" \
  sh "$fixture/run-on-owned-simulator.sh" \
  "$base/build/derived-data/Build/Products/UP5Theme_iphonesimulator27.2-arm64.xctestrun"
```

The XCTest captures native Text and Button screenshots and checks light and
dark V2 inks and fills during both bundled and signed guest display. A
disabled sibling comes from each document. The signed app stages a locally
signed Wasm payload, waits for native display health, and asserts that a
native Save writes the exact expected storage bytes. The fixture uses the
production capability presentation and performs no private display
acknowledgment or authority injection. The light fixture colors and the
screenshot sampling method come from the successful S4 fixed-light
experiment. Running on 26.5 leaves an actual iOS 17.x launch pending. The
pressed, increased-contrast, and Bold Text mappings also still need native
rendering evidence.
