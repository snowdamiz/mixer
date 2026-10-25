# Apple keyboard focus diagnostic V1: generic simulator compilation

The accepted six-source diagnostic derivative compiled successfully on the first
attempt. MixerCore, MixerUI, the diagnostic app, and the XCTest runner each
returned exit code 0. This establishes Swift compilation only. No simulator or
device inventory, boot, app launch, test execution, UI, screen capture, physical
phone query, network request, or signing credential operation was selected.
The original failed `actualNativeFocusTraversal` predicate remains unresolved.

The producer command, from the repository root, was:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1-build/build.py
```

`build.py` requires a fresh owned scratch/receipt destination and refuses to
overwrite a retained attempt. It imports only the inspected standalone
`verification/apple-toggle-keyboard-focus-diagnostic-v1/prepare.py`. The six
rendered outputs are data; no bridge, harness, runtime, composition, or authority
module is imported or executed. The V9 source lock and V3 runner provenance
bind every copied original source. The accepted preparation generator, local
snippets, patch, manifest, immutable inputs, and root acceptance are also bound.

The app uses retained V9 Swift sources and the reviewed three Swift app overlays.
The runner uses the unchanged V3 Xcode project and support sources, plus the
reviewed XCTest source overlay. Both prepared Python files are retained in the
compact source archive as data. There is no diagnostic compiler correction or
change to focus behavior, the oracle, the first acquisition Tab, input methods,
or timing budgets. The accepted packet and all bound originals remain unchanged.

Observed tools were Xcode **26.6, build 17F113**, Apple Swift **6.3.3**
(`swiftlang-6.3.3.1.3`), iPhoneSimulator SDK **26.5**, and Python **3.14.8**.
The exact version stdout, executable/SDK metadata hashes, command argument arrays,
environment overrides, timeouts, elapsed times, exit codes, and raw compiler
stdout/stderr are retained under
`verification/apple-toggle-keyboard-focus-diagnostic-v1-build/`.

The app modules and executable were compiled directly with the pinned Swift
compiler, `-swift-version 6`, and `-target arm64-apple-ios26.0-simulator`.
The runner used the pinned `xcodebuild build-for-testing` with
`-destination 'generic/platform=iOS Simulator'`, `ARCHS=arm64`,
`IPHONEOS_DEPLOYMENT_TARGET=26.0`, automatic package resolution disabled, and
code signing disabled. No simulator-specific destination was queried or used.
The inherited review revision is
`ba9ad4372f94463ba4d363cdfd76dd565c96413f`; no Git command was run by this lane.
`source-manifest.json` records the actual materialized tree digest separately.

The compiler reported existing app API deprecations and existing XCTest setup and
teardown actor-isolation warnings, plus Xcode metadata/support-library warnings. No
diagnostic API/type error occurred. These warnings were retained without source
changes. Compilation does not verify teardown safety or public focus APIs at
runtime.

The diagnostic app's owned product plist raises `MinimumOSVersion` from its
retained source value `17.0` to `26.0` to match the compiled deployment target.
`packaging-derivation.json` binds this packaging-only derivative; the accepted
plist is unchanged. There was no explicit signing command. Linker signatures
and Xcode's pre-signed XCTest support frameworks remain as produced/copied by
the platform tools; no signing credential was accessed.

`products.tar.gz` retains the app and runner Build/Products only, including the
generated `.xctestrun`, in **8,824,075 bytes**. Its SHA-256 is
`5ff6e5b7a7a6c11b251e9841a63c6c3afe669f42cf62679f8d7995f985e20bba`.
`product-manifest.json` binds every file, mode, and symbolic link and the complete
product tree. `accepted-sources.tar.gz` retains the 39 materialized source files
in **81,260 bytes**, with SHA-256
`5b7f6b663e71b0ce56bb016bb0c42e5e30b622d20469e0a47b89cab352625e32`.

The product archive was read back and verified before cleanup. Only this lane's
owned `scratch` directory was removed, accounting for **164,544,692 file bytes**;
it included the new compiler caches, build intermediates, copied sources, and
temporary export. No old build tree was copied. Other projects' processes,
simulator instances, and data were untouched. No native instance was created.

An independent byte audit can be rerun without compilation or extraction:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-toggle-keyboard-focus-diagnostic-v1-build/audit.py
```

The observed audit passes: every retained source and product archive entry,
all original input bindings, and the six reviewed prepared hashes match.
Mach-O load commands for the three app binaries and compiled XCTest bundle
confirm arm64, iOS Simulator platform 7, minimum OS 26.0, and SDK 26.5. The app
product plist also requires iOS 26.0. The source archive was independently
verified after scratch removal; cleanup records preserve this ordering.

These compact products support a separately selected later native run. No new
execution packet or runtime selection is made here. UIKit/XCTest semantics,
diagnostic timing interference, the first-Tab destination, native acceptance,
carrier/OTA release, immutable published-package FieldLog dogfood, signing,
store, customer, operational, and GA gates remain unverified. Physical phones
remain disconnected and deferred.
