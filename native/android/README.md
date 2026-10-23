# Owned native Android adapter development slice

This W05 slice uses the Android widget toolkit through independently authored Java and a small C JNI bridge. Swift owns the checklist model, reducer behavior, UI document authoring, node generations and authoritative event routing. The shared library uses the actual local MixerUI SDK source; Java has no duplicate checklist business logic. This is development integration, not FieldLog D2 or published-package qualification.

The example is an editable project title and checklist: text edits update the Swift title; a draft plus Add button appends a stable-ID task; native toggles update completion counts; reversing the list preserves logical generations and native View instances. UTF-8 text including accented, CJK and non-BMP characters crosses the byte-array JNI boundary.

The updated product plan section 8.3 requires shared-theme design parity with the
iOS app. This adapter's current Android default controls and hardcoded visual
values do not meet that requirement. Shared appearance/schema and renderer work
remain open; platform-specific app appearance must be explicitly declared. Native
accessibility, navigation, text input and system-owned surfaces retain their
platform behavior. Earlier physical interaction receipts do not verify design
parity. Side-by-side physical reference-screen review is pending while phones are
disconnected.

## Reproduce

```sh
python3 native/android/verify.py --device 38031FDJG00JEF
```

Without `--device`, verification runs the five Swift host tests, 34 Java wire-contract checks and APK build only. A physical run installs `native/android/build/mixer-android-debug.apk`, runs the owned platform Instrumentation checks, then performs native touch/keyboard input and a touch toggle. XML and screenshots show the task and Swift-owned completion count. The verifier requires the instrumentation's explicit pass marker because `am instrument` can return process exit 0 after an app crash. It also rejects any source change during verification. Exact commands, outputs, SDK source hashes, tool versions, APK identity and device properties are under [verification/receipt.json](verification/receipt.json).

Build only with `python3 native/android/build.py`. The script invokes the official Swift compiler, NDK Clang/JNI headers, javac, D8, aapt2, zipalign and apksigner. It assembles the dependency closure from the official Swift Android runtime and NDK `libc++_shared.so`. It does not use generated project scaffolding, Gradle plugins, competitor code or external engine dependencies. The local debug key lives in ignored `build/`, and no production signing or store upload occurs.

Pinned local tools: open-source Swift 6.3.3 and matching Android SDK, exact SDK ID `aarch64-unknown-linux-android28`; NDK r27d; Android platform/build tools 37; JDK 25 compiling Java 17 bytecode. `DEVELOPER_DIR` is scoped to Xcode 26.6 for the host manifest/compiler environment. Selecting an artifact name plus `--triple` previously selected incorrect x86 resource paths; the build uses the exact SDK ID. These are local tool choices, not a universal supported-toolchain release.

## Public bridge and Android profile

[bridge/mixer_android.h](bridge/mixer_android.h) defines the owned C ABI. Sessions are bounded to 16 and have monotonically assigned, never-reused handles. Destroy invalidates the handle; stale/foreign handles reject. Swift serializes access through a lock. `mixer_android_exchange` borrows caller-owned input/output buffers only for the call and retains no pointer. Render and dispatch use bounded buffers; failed event validation or insufficient output capacity leaves Swift state unchanged. No Swift error crosses C. The caller must still provide valid foreign pointers; arbitrary dangling pointers cannot be made safe by a buffer contract.

JNI copies byte arrays using region APIs, releases every C allocation on all paths, retains no Java reference, checks pending JNI exceptions, and never passes Swift UTF-8 to Java's modified-UTF8 APIs. Java byte arrays own returned payloads. The renderer requires Android's UI thread. There are no asynchronous callbacks, cross-thread UI updates, arbitrary selectors or capability calls in this bridge.

The packet is `{"schemaVersion":1,"document":<existing UI schema1>,"identities":[{"id":"...","generation":1}]}`. Android requires exact identity coverage and preserves the SDK's full UInt64 revision/generation values through decimal tokens. Events use the SDK's existing `UIEventEnvelope` shape: revision, identity, event, value. Caller-supplied action IDs never authorize behavior; Swift resolves the current binding again. Both sides reject stale revision/identity, disabled/unbound events, mismatched values, malformed/oversized data and duplicate keys (including escaped collisions).

The owned Java decoder validates an entire candidate before renderer changes. It enforces the schema-1 node/property/action rules, 1MiB packet bytes, 4,096 nodes, 64 UI levels, 1,000 children, 128-byte IDs, 16KiB UTF-8 property strings, 16 properties and four actions. Construction is also bounded to 196 JSON levels, 100,000 JSON values and 16,384 members per collection. Unknown fields/kinds/properties/actions reject. The Android profile further rejects nested scrolling lists and hStack first/last-baseline alignment. Accessibility state values require API30; those values reject on older devices. The profile is recorded in [contracts/android-profile-v1.json](contracts/android-profile-v1.json).

Native mappings: TextView, EditText, Button, Switch, LinearLayout, FrameLayout and ScrollView render text/input/buttons/toggles/stacks/sections/navigation-root/list. Children are reconciled by authoritative identity; scalar changes and same-parent reorder reuse Views. There is no list virtualization. Labels, tooltips and state descriptions map to platform accessibility fields; accessibility identifiers are native View tags. Disabled state includes ancestors. Destructive buttons receive destructive text styling; cancel buttons use normal Android button styling and dispatch their authored action. Navigation is one root container, with no destination/back/sheet behavior.

## Evidence and limits

The physical receipt is for Pixel 8 Pro serial `38031FDJG00JEF`, Android 17/API37, arm64 only. It verifies actual Swift shared-library execution through JNI and native widgets. Host tests cover Swift model/event transactionality, duplicate keys, input/output limits, capacity failure, handle exhaustion/destruction, Java schema/Unicode/bounds/event mismatch and revision/generation rules. The initial framework-tag-key launch failure was fixed by retaining text watchers on owned adapter records; final verification was rerun.

A scoped independent bridge/wire review reproduced and fixed acceptance of non-ASCII digits in JSON Unicode escapes. Java now accepts only ASCII hexadecimal digits, and the physical receipt was rerun with 34 contract checks. Verification records observed pass counts, SDK revision/dirty state and physical-versus-emulator identity instead of hardcoded qualification claims. See `verification/independent-review.json`.

Still open: broader independent security/renderer review; immutable SDK publication and a separate FieldLog consumer; FieldLog D2; TalkBack and accessibility focus/actions; IME composition, locale, hardware keyboard and selection matrices; retained focus/scroll across reparenting; process recreation/persistence; async effects/lifecycle cancellation; large-list/frame/memory performance; other OS/API/ABI/device targets; 16KiB-page fleet qualification; production signing/store acceptance. The example's state currently resets when a new Activity session is created. Native UI rendering is synchronous with a whole-document event round trip; no frame-rate or latency budget is claimed.

Normative platform references are [Android JNI guidance](https://developer.android.com/ndk/guides/jni-tips), [platform Instrumentation](https://developer.android.com/reference/android/app/Instrumentation), and the [official Swift Android SDK guide](https://www.swift.org/documentation/articles/swift-sdk-for-android-getting-started.html). The implementation uses the locally pinned matching 6.3.3 toolchain/SDK rather than assuming the guide's latest version is installed.
