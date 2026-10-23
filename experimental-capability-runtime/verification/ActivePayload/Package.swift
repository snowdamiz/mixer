// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "ActivePayloadObservation", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../.."), .package(path: "../../../sdk")],
    targets: [.executableTarget(name: "active-payload-observer", dependencies: [
        .product(name: "MixerExperimentalCapabilityRuntime", package: "experimental-capability-runtime"),
        .product(name: "MixerCapabilities", package: "sdk")])])
