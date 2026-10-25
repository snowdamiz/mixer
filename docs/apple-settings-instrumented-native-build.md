# Instrumented Settings runner build

The accepted first-failure diagnostic is now compiled into fresh simulator XCTest products. The existing application and its libraries remain byte-identical: all 13 application product files match the prior reviewed package. Only the test runner is rebuilt.

The frozen accepted source archive gains the reviewed diagnostic helper, its Xcode project references and the reviewed change to ToggleUITests.swift. DiagnosticTransport.swift, PublicSwitchSelection.swift, the test sequence and all application sources remain unchanged. The new archive contains 40 source files and the composed product archive contains 55 files. Generic simulator build-for-testing passes with Xcode 26.6 / SDK 26.5 / minimum iOS 26.0; no native instance or test execution is selected by this build.

The runner build retains seven warnings with exactly the same messages as the previous runner: six XCTest setup/teardown actor-isolation warnings and one absent-AppIntents metadata warning. The separate complete source typecheck was warning-free; the actual build result is reported separately here. No warning is suppressed or newly introduced by the diagnostic source change.

[The build receipt](../verification/apple-settings-instrumented-native-build/attempt-1/receipt.json) records exact source/tool/product hashes, commands, output and scope. All four command groups exit zero with complete streams, no timeout/signals and no surviving owned processes. Scratch is removed after archive verification and a clean holder check. No signing credential, physical phone, UI automation or screenshot is used.

The next step is a fresh bounded runtime composition and review using these products and the already reviewed strict importer/oracle. The previous Settings timeout and skipped Tab test remain failures; compiler success does not qualify keyboard behavior, FieldLog, store, deployment or GA.
