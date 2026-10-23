// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "MixerCapabilityQualification", platforms: [.macOS(.v14), .iOS(.v17)],
    dependencies: [.package(path: "../sdk")], targets: [
        .executableTarget(name: "capability-probe", dependencies: [.product(name: "MixerCapabilities", package: "sdk")], path: "Probe"),
        .executableTarget(name: "guest-transport-probe", dependencies: [.product(name: "MixerCapabilities", package: "sdk")], path: "GuestTransportProbe"),
        .testTarget(name: "MixerCapabilitiesTests", dependencies: [.product(name: "MixerCapabilities", package: "sdk")])
    ], swiftLanguageModes: [.v6])
