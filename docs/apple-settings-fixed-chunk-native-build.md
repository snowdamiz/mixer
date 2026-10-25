# Fixed4992 generic simulator runner build

The root-selected fixed4992 XCTest runner builds successfully from the exact
reviewed source closure. This is generic simulator `build-for-testing` evidence;
no native test execution or Settings/Tab acceptance is selected or established.

The root selection is
`verification/apple-settings-fixed-chunk-root-review/acceptance.json`, SHA-256
`2addcd0f2b37463241cec8451b444cb4b933ce5dfcf5b2f0ecec483aae2b7db8`,
with controller revision `be472ce6424a691de5673e3438d2768264827d23`.
Before and after the build, all 176 producer, 163 independent-review, and 22 prior
accepted-build handoff members match their pinned identities. The reviewed source
package is `585f44532cb67ca626ae7c2c95bfa7030408bf2b4dc57f5bac0fdbd84cea66af`.

The freshly materialized compile closure contains 40 regular files. Exactly one
file differs from the prior accepted compile closure: reviewed
`ToggleUITests.swift`, SHA-256
`0e43bd202946711ff6f1c89c8ebeb7d26f692f7ab4d5ec862e67e674f3765fb3`.
The project, scheme, other three exact UIKit/XCTest Swift files, and all other
sources are unchanged. All four source hashes match the independent complete
typecheck. This lane does not include the receiver or change any protocol,
budget, application, oracle, importer, transport, failure diagnostic, capture,
action, termination, attachment, or semantic contract. The accepted receiver
endpoint remains bound by the upstream handoffs for a later coordinated step.

The source archive SHA-256 is
`96cf2e6d4356035e004564a2a4d4e01122fb570835e4089c6c83788ab53465f8`;
its canonical 40-file tree digest is
`0677712483e4f078cbd10120efd5c9f9d4a13fe31b9f455caa1a984772d2bfeb`.
It is built in a new owned scratch directory, with no old derived data or runner
products copied into the build. Project semantics and argv match the prior
accepted generic build after substitution of the owned scratch path.

Apple Swift 6.3.3 from Xcode 26.6 (17F113) and iOS Simulator SDK 26.5 compile
the runner for arm64 / minimum iOS 26.0. The destination is
`generic/platform=iOS Simulator`; code signing, compiler indexing, automatic
package resolution, and package updates are disabled as in the accepted build.
The Swift driver SHA-256 is
`2ed38571e92c0283091838c1649e27650ad9c99950288e883c7b2dc6c4ce89fb`.
Exact tool paths, resolved SDK, tool bytes, version streams, argv, environment,
source and product identities are retained in the build evidence.

The product archive SHA-256 is
`cca8472579ed6ce7c3c00babadb44d37ba34dc1a400ec00fc7802536342d7a2c`;
its canonical 55-file tree digest is
`58835bb84bfdf801a395a237c6ea6dfdd746ca005c9533736ec2ee5cf80fa4b8`.
It contains 42 files from the fresh runner build, including copied Apple test
frameworks, and the exact 13 original application/library product files from the
original frozen qualification archive. Those 13 application files are reused,
not freshly built, and are verified byte-for-byte with their original manifest.
The archived headers are confined regular-file members, with explicit modes and
fixed archive metadata. Nothing is extracted by the read-only verifier.

All 15 actual `warning:` lines match the message multisets in both the original
qualification log and prior accepted runner log: six XCTest setup/teardown
actor-isolation warnings, one missing-AppIntents metadata warning, and eight
warnings about stripping already signed Apple test framework/library binaries.
The prior summary's seven-warning count covered only the compiler/metadata
subset; its retained stdout already contained all 15. No warning is suppressed
or newly introduced, and all streams are retained. Framework-copy order can vary,
so comparison preserves ordered lists and checks the full message multiset.

[The receipt](../verification/apple-settings-fixed-chunk-native-build/attempt-1/receipt.json)
records a passing first build. The four command groups and enclosing Python
driver all exit zero, reach stdout/stderr EOF, have no timeout or sent signal,
and leave no owned process-group members. After compact archives and manifests
are verified and `lsof` finds no scratch holders, 108,699,784 bytes of owned
scratch, derived data, and module caches are removed. Other projects and native
instances are untouched. No simulator inventory/create/boot/install/run, device
query, UI, screen capture, phone, listener, hosted operation, or explicit network
operation is performed. Package updates/resolution are disabled.

The handoff seal is in
`verification/apple-settings-fixed-chunk-native-build/handoff.sha256`.
The verification command is read-only and prints JSON without writing a result:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -B verification/apple-settings-fixed-chunk-native-build/verify.py
```

It rechecks every sealed member and all pinned upstream handoff members, the
safe source/product archives and exact manifests, the one-file compile-closure
delta, all four reviewed Swift hashes, the 13 original application identities,
the unchanged generic build argv, process/EOF/exit receipts, complete warning
comparison, and scratch absence. It neither rebuilds nor prepares execution.

The first sealed-verifier invocation failed because its lookup assumed a
`swift-driver` resolved path; this Xcode's `swiftc` resolves to `swift-frontend`.
The pinned compiler hash was already correct. The failed verifier, seal, exact
tool-output error and failure receipt are retained under `attempt-1-seal/`.
The second verification attempt then found that its lane inventory excluded
historical nested handoff filenames as well as the current top-level seal. That
verifier and error are retained under `attempt-2-seal/`; the exclusion now applies
only to the current top-level seal files. These are verifier-only corrections;
no source, build, product, warning, command or cleanup receipt changes. One
documentation patch context mismatch was also observed and corrected before
sealing; it made no partial edits and is recorded in `editing-notes.json`.

Importer rebinding, a fresh bounded runtime composition, and independent review
remain separate work. The original V6 Settings failure, dependent Tab skip,
Xcode exit 65, and strict importer rejection remain authoritative. Compiler
success does not establish runtime networking, keyboard/carrier behavior,
physical-phone acceptance, immutable external FieldLog qualification, signing,
store, customer, operational, or GA acceptance. Physical phones remain
disconnected and deferred. Frozen hosted-inspector/authority and rejected
outbound-worker transport lanes are outside this build.
