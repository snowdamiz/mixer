// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "IndependentAndroidReview", platforms: [.macOS(.v14)],
    dependencies: [.package(path: "../source/sdk"), .package(path: "../source/native/android/engine")],
    targets: [.testTarget(name: "IndependentAndroidReviewTests", dependencies: [
        .product(name: "MixerUI", package: "sdk"), .product(name: "MixerAndroidRuntime", package: "engine")])],
    swiftLanguageModes: [.v6])
