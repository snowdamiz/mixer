// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "BridgeCrossProbe", platforms: [.iOS(.v17), .macOS(.v14)],
    dependencies: [.package(path: "../.."), .package(path: "../../../sdk")],
    targets: [.executableTarget(name: "bridge-cross-probe", dependencies: [
        .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
        .product(name: "MixerCapabilities", package: "sdk")])])
