// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "ReviewPairAndroid", platforms: [.macOS(.v14)],
    products: [.library(name: "AppAndroid", type: .dynamic, targets: ["AppAndroid"])],
    dependencies: [.package(name: "Application", path: "../.."), .package(path: "../../Generated/MixerAndroid"), .package(path: "../../Generated/MixerSDK")],
    targets: [
        .target(name: "AppAndroid", dependencies: [.product(name: "AppFeatures", package: "Application"), .product(name: "MixerAndroidRuntime", package: "MixerAndroid")]),
        .testTarget(name: "AppAndroidTests", dependencies: ["AppAndroid", .product(name: "MixerUI", package: "MixerSDK")])
    ], swiftLanguageModes: [.v6])
