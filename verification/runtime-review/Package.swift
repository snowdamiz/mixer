// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "ReadOnlyRuntimeReview", platforms: [.macOS(.v14)], dependencies: [
    .package(path: "../../runtime")
], targets: [.testTarget(name: "ReviewTests", dependencies: [.product(name: "MixerRuntime", package: "runtime")])], swiftLanguageModes: [.v6])
