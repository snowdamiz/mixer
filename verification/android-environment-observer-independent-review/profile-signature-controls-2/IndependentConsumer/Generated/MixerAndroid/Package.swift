// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "MixerAndroid", platforms: [.macOS(.v14)],
    products: [.library(name: "MixerAndroidRuntime", targets: ["MixerAndroidRuntime"])],
    dependencies: [.package(path: "../MixerSDK")],
    targets: [.target(name: "MixerAndroidRuntime", dependencies: [
        .product(name: "MixerCore", package: "MixerSDK"), .product(name: "MixerUI", package: "MixerSDK")])],
    swiftLanguageModes: [.v6])
