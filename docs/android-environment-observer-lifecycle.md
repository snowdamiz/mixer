# Android environment observer lifecycle

This slice repairs the existing private `NativeEnvironmentV2.Observer`. The
observer has eight bounded registration slots. It records possible ownership
before each add, retains each actual removal target, retires before terminal
callbacks, and attempts every eligible removal independently. If an add reenters
close or detach before acquiring, cleanup defers that in-flight slot until the
add returns or throws; construction then unwinds and cannot acquire another slot.
A completed observer is published only after all eight registrations return.

All observer entries and delivered callbacks enforce the main-Looper check before
stale-state guards. Retired callbacks cannot read a tuple, change its generation,
or notify the renderer. Detach and generation exhaustion retire before renderer
invalidation. Registration-time notifications still synchronously invalidate
renderer gates, while capture refuses an incompletely registered observer.
The existing second synchronous environment read remains authoritative.

Cleanup consumes a slot before removing it, so reentrant or repeated close cannot
retry it. The focus listener uses the exact stored `ViewTreeObserver`; replacement
observers are untouched. A dead stored target is reported as uncertain without a
removal call. Fixed eight-entry diagnostic arrays distinguish possible ownership,
removal in progress, returned removal, failed uncertain removal, and dead uncertain
target. A returned platform method alone does not prove actual reclamation.
The first failure remains retained; an `Error` from acquisition, renderer
invalidation or cleanup escapes with precedence over an ordinary runtime failure.
Suppression is best effort after independent cleanup; allocation failure cannot
truncate remaining removal attempts.

The inset setter belongs solely to the existing private dedicated V2 root during
this observer's lifetime. Its creator must not install a competing inset listener.
This does not compose an arbitrary preexisting listener. Public `MixerActivity`
continues its existing V1 root and padding path. Public integration requires its
own root owner and safe-area/padding composition contract.

The explicitly selected successor is `mixer.android-source-pair.2`: the same 22 SDK
and 20 adapter members, with only `NativeEnvironmentV2.java` changed. The SDK
projection, descriptor, Android profile ID, appearance format/recipe, document and
packet schemas and private C ABI are unchanged. The Swift policy remains the sole
literal map; the rendered Python driver receives that policy. Old profile 1 locks
require the newer first-party CLI and fresh project recreation; local edits and
recomputed generic locks do not qualify changed sources. Historical profile 1
packets remain intact.

The bounded host runner compiles the actual observer with 28 independently
authored faulting Android/renderer leaves and its package-peer tests. An explicit
source list and source identities are frozen before execution. These leaves are
host fault controls, and cannot establish native Android behavior. The runner
strips implicit JVM option/classpath variables, uses an empty classpath and
sourcepath with `--release 17 -Xlint:all -Werror -proc:none`, retains command streams
and class hashes, reaps its owned children, and removes its owned scratch.

Host attempt 1 failed before compilation because `/usr/libexec/java_home -v 17`
found no registered JDK. Attempts 2 and 3 use the installed Homebrew OpenJDK 25
with the Java 17 release policy; both pass 161 cases. Attempt 3 additionally checks
the capture root accessor's main-thread assertion. Each attempt preserves its
source freeze and inputs. These are producer host results pending independent
review, not native platform acceptance.

The [frozen candidate proposal](../verification/android-environment-observer-lifecycle/candidate-proposal.json)
(9,252 bytes, SHA-256 `80eed4b279283d073f745061eb071aff7daa7b4369cbabd9e4b97fab6ff98b8a`)
received [root admission](../verification/android-environment-observer-root-review/profile-candidate-admission.json)
before dependent qualification. The observer is 14,318 bytes with SHA-256
`814b00b91b458c1287cb9c924c099fc2e647e42501b09e09acd711fbe5b54dac`;
the new adapter projection is
`43f22eeaa7480ef9c0a8fdb50addff4edaeea83319488605c5db3b2d782f1ef5`.
No candidate product/profile source changed after admission.

[Profile qualification attempt 1](../verification/android-environment-observer-lifecycle/profile-qualification-1/receipt.json)
failed before tests: official Swift 6.3.3 host manifest compilation against the
installed macOS 27 SDK reported unknown `-target-arch-variant` arguments and
signal 11. Its streams and frozen inputs remain retained; its owned build
scratch was removed. [Attempt 2](../verification/android-environment-observer-lifecycle/profile-qualification-2/receipt.json)
used installed Xcode Apple Swift 6.4 for host compilation. It passed ten Swift
admission test functions, including their parameterized cases, nine Python
regressions, actual CLI project creation and identical copied export under
profile 2, four app-owned shared-feature tests, and three app-owned native-session
host tests. Actual CLI and rendered-driver calls reject historical profile 1
locks, same-size observer edits, and edited sources with recomputed generic
locks. Driver sentinels independently refuse generic hashing, tool discovery and
output before admission; a profile 1 rendered policy is refused before lock read.
The exact source snapshots and all command streams are retained.

[Direct cross-compilation](../verification/android-environment-observer-lifecycle/cross-compilation-1/receipt.json)
rechecked the complete creation toolchain lock. All fourteen actual adapter Java
sources compiled to 160 classes against the installed locked Android 37 SDK jar
with Java 17 release policy. D8 `--min-api 28` produced a 256,904-byte DEX with
SHA-256 `e67af9f18f6d0456886dcdad65f52b2fb04ef5c7aec6fa26c357d79f201bb883`.
Official Swift 6.3.3 with its Android SDK/NDK r27d compiled the created app's
ordinary AppModels/AppFeatures factory/reducer and private staged exports to an
arm64 ELF, SHA-256
`8cced671e3ba150bfed5e36795ade2e7026c1c34a52c6780dac92805af4343cd`.
The actual JNI bridge linked to it with no undefined symbols and produced an
arm64 ELF, SHA-256
`181f44f5a3d1e4d7c05916f74b008073b77686f4e635d92cd1d996ea7196ecaa`.
Classes, DEX and ELF identities, tool binaries/distributions/metadata, exact argv,
versions and complete streams are recorded. All owned compile scratch was
removed and owned children reaped. No signing, APK publication or top-level
`native/android/build.py` execution occurred.

These are host and compile-only results awaiting independent implementation
review. D8 min API 28 and SDK 37 compilation do not establish API 28–35 support.
Native runtime, computer use and capture remain paused. Public V2 routing, the effect runner,
API 28–35 support, unsupported accessibility/resources/fonts, saved-state
continuity, immutable separate-repository FieldLog packages, final phones,
signing/store/operational and accountable GA acceptance remain pending. This
slice grants no OTA or release authority.
