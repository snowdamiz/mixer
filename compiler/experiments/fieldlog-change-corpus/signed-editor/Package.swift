// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "SignedFieldLogEditorHost",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "sdk"),
        .package(path: "updates"),
        .package(path: "experimental-capability-runtime"),
        .package(path: "swift-crypto"),
    ],
    targets: [
        .target(name: "FieldLogModels", path: "fieldlog/Sources/FieldLogModels"),
        .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"], path: "fieldlog/Sources/FieldLogStorage"),
        .executableTarget(name: "EditorHost", dependencies: [
            "FieldLogModels", "FieldLogStorage",
            .product(name: "Crypto", package: "swift-crypto"),
            .product(name: "MixerUpdates", package: "updates"),
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerGuest", package: "sdk"),
            .product(name: "MixerCapabilities", package: "sdk"),
            .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime")
        ], path: "host"),
    ],
    swiftLanguageModes: [.v6]
)
