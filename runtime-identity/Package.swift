// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerRuntimeIdentity", platforms: [.iOS("26.0"), .macOS(.v14)],
    products: [
        .library(name: "MixerRuntimeIdentity", targets: ["MixerRuntimeIdentity"]),
        .executable(name: "mixer-identity", targets: ["MixerIdentityTool"]),
    ],
    dependencies: [.package(path: "../updates")],
    targets: [
        .target(name: "MixerRuntimeIdentity", dependencies: [.product(name: "MixerUpdates", package: "updates")]),
        .executableTarget(name: "MixerIdentityTool", dependencies: ["MixerRuntimeIdentity"]),
        .testTarget(name: "MixerRuntimeIdentityTests", dependencies: ["MixerRuntimeIdentity"], resources: [.copy("Fixtures")]),
    ],
    swiftLanguageModes: [.v6]
)
