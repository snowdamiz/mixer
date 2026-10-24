// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "SignedGrantPolicyCheck", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../../../../sdk"), .package(path: "../../../../updates")],
    targets: [.executableTarget(name: "grant-policy-check", dependencies: [
        .product(name: "MixerCapabilities", package: "sdk"), .product(name: "MixerUpdates", package: "updates")
    ])]
)
