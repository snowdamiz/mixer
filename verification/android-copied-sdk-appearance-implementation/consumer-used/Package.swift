// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "PairConsumer", platforms: [.iOS("26.0"), .macOS(.v14)],
    products: [.library(name: "AppFeatures", targets: ["AppFeatures"])],
    dependencies: [.package(path: "Generated/MixerSDK")],
    targets: [
        .target(name: "AppModels"),
        .target(name: "AppFeatures", dependencies: ["AppModels", .product(name: "MixerUI", package: "MixerSDK")]),
        .testTarget(name: "AppModelsTests", dependencies: ["AppModels", "AppFeatures"])
    ]
)
