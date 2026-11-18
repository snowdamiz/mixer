// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "FieldLogTrial", platforms: [.macOS(.v14)],
    products: [.executable(name: "fieldlog-host", targets: ["Trial"])],
    dependencies: [.package(path: "../capability-activation"), .package(path: "../sdk"), .package(path: "../updates"), .package(path: "../runtime-identity"), .package(path: "../swift-crypto")],
    targets: [.target(name: "FieldLogModels", dependencies: [], path: "FieldLogModels"), .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"], path: "FieldLogStorage"), .target(name: "FieldLogDraftIntegration", dependencies: ["FieldLogModels", "FieldLogStorage", .product(name: "MixerCapabilities", package: "sdk")], path: "FieldLogDraftIntegration"), .executableTarget(name: "Trial", dependencies: [.product(name: "MixerCapabilityActivation", package: "capability-activation"), .product(name: "MixerRuntimeIdentity", package: "runtime-identity"), .product(name: "MixerCapabilities", package: "sdk"), .product(name: "MixerUpdates", package: "updates"), .product(name: "Crypto", package: "swift-crypto"), "FieldLogModels", "FieldLogStorage", "FieldLogDraftIntegration"], path: "Sources")],
    swiftLanguageModes: [.v6])
