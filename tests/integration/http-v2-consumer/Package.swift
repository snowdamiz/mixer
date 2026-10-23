// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "HTTPReleaseProtocolConsumer", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../../../updates")],
    targets: [.executableTarget(name: "http-release-check", dependencies: [.product(name: "MixerUpdates", package: "updates")])]
)
