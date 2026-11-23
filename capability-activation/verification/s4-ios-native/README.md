# Replay S4 iOS feature ownership

This §24.6 B' fixture uses `MixerGuestScreen`, the ABI 2 signed Save program, local development trust, and an app-private store per test UUID. It applies one fixed-light theme to native SwiftUI text and buttons. The running fixture needs no service or credentials.

## Build

Use arm64 macOS, Xcode 27.2 (27B52), Python 3.11 or later, Ruby with the `xcodeproj` gem, and Rust 1.99.0 with `llvm-tools` and the `aarch64-apple-ios-sim` target. SwiftPM uses the pinned package resolution and needs access to the pinned Swift Crypto checkout on a cold build.

```sh
# From the repository root
fixture=capability-activation/verification/s4-ios-native
plan=$("$fixture/build.sh")
```

The script creates a fresh ignored `verification/local/s4-ios-native-replay.*` directory and prints its path to stderr. It builds the VM at `692f05cd2d31f218ae9b3cef7253a4e7397f8e17`, archives the five Swift package inputs at `a332356703122de8393115e8e8d42badca6aa1e0`, and compiles the test app and XCTest runner with the generic iOS Simulator destination. That package tree includes the published first-display gate from `35ab3dbd363a5a951dca752df1fcbb953e37a901`. The preparation step instruments only the copied package files for receipt holds, readback, callback capture, and the fixture theme. It records the resulting input provenance in `inputs.json`. Both apps are signed ad hoc. The app, runner, and XCTest bundle target iOS 17.0 and arm64 Simulator. Keep the printed `.xctestrun` with its adjacent products.

## Run on the root-owned iOS 26.5 Simulator

Root used Xcode 27.2 with a disposable iPhone 15 on iOS 26.5 (23F77). Make a fresh public Accessibility check from the root launcher before provisioning a device. On the affected macOS 27 host, re-adding `/Users/andreyyurlov/Applications/Acid.app` in Device Control and Data Access restored trust. [Repository device rules](../../../AGENTS.md)

```sh
build_dir=${plan%/derived-data/Build/Products/*}
TMPDIR="$build_dir/tmp/" xcrun clang -x c -framework ApplicationServices \
  -o "$build_dir/ax-trust" - <<'C'
#include <ApplicationServices/ApplicationServices.h>
#include <stdio.h>

int main(void) {
    bool trusted = AXIsProcessTrustedWithOptions(NULL);
    puts(trusted ? "AX_TRUSTED=1" : "AX_TRUSTED=0");
    return trusted ? 0 : 1;
}
C
"$build_dir/ax-trust"
```

Require `AX_TRUSTED=1`, snapshot the external device baseline under the repository's ownership rules, and wait for `xcrun simctl bootstatus "$OWNED_SIMULATOR_UDID" -b` on the exact new UUID.

```sh
# With OWNED_SIMULATOR_UDID set to that already booted test instance
export OWNED_SIMULATOR_UDID
"$fixture/test.sh" "$plan" controls

# Optional additional test with its own result bundle and fresh fixture UUID
"$fixture/test.sh" "$plan" healthy-callback
```

Each invocation writes to a new `tests.*` directory below the build, with a log, result bundle, summary, and XCTest attachments for each selector. Keep `fixture-ids` and `s4-boundary-readback` with the candidate, launch, and process identifiers. Root shuts down the exact owned device, confirms `Shutdown`, deletes that UUID, and records its absence and the external baseline comparison. Leave the shared Simulator frontend running. After command and device custody are established, retain the desired evidence and remove only the exact build directory printed by `build.sh`. Preserve any unresolved custody and its output.

## Evidence

Root's combined build passed the invalid-first-frame, signed rollback and offline relaunch, and shared-theme controls. The theme test compares the themed bundled and signed guest pixels against a platform-style bundled control. The combined recovery selector reached the owner replacement and failed at the original fresh-process assertion.

The corrected recovery selector passed in root's separate run. It covers the disabled native Save while the exact first receipt is held, a single delivered Save after acknowledgment, stale callback refusal on revision 3, and a duplicate native screen causing `presentationInvariant` at `intentEntered`. It uses two stores after the fault. The callback store keeps `ui_protocol_after_effects` through failed-owner retirement and replacement health, then records `effects_closed` on ordinary replacement close. The offline store is reopened in a new process after failed-owner retirement with no intervening replacement launch. It retains `ui_protocol_after_effects`, accepted sequence 2, and `AAH+/w==`. That selector also invokes the provisional renderer's captured callback after actual owner and screen replacement.

The additional selector captures the routed Save callback installed when the original renderer is healthy and enabled at revision 1. It closes that owner, mounts a healthy replacement at the same revision and candidate in the same process, and invokes the original callback directly. It checks that the replacement stays at revision 1 with no accepted or delivered event or disk write. A native Save on the replacement is the positive control. The additional selector has compiled and awaits native execution.

The replay receipt records the original fixture, the validated recovery source and build manifest, the root runs, and the fresh generic build. Runtime verification at the iOS 17 floor, FieldLog delivery, and physical-device qualification are separate. [Replay receipt](receipt.json)
