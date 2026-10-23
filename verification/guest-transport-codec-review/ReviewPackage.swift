// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "IndependentGuestTransportReview", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../source/sdk")], targets: [
        .testTarget(name: "PublicCodecReviewTests", dependencies: [.product(name: "MixerCapabilities", package: "sdk")], path: "Tests")
    ], swiftLanguageModes: [.v6])
