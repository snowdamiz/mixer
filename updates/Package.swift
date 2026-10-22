// swift-tools-version: 6.2
import PackageDescription
let package = Package(
    name: "MixerUpdates", platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "MixerUpdates", targets: ["MixerUpdates"]), .executable(name: "mixer-update", targets: ["MixerUpdateTool"])],
    dependencies: [.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")],
    targets: [
        .target(name: "MixerDurableIO"),
        .target(name: "MixerUpdates", dependencies: ["MixerDurableIO", .product(name: "Crypto", package: "swift-crypto")]),
        .executableTarget(name: "MixerUpdateTool", dependencies: ["MixerUpdates"]),
        .testTarget(name: "MixerUpdatesTests", dependencies: ["MixerUpdates", .product(name: "Crypto", package: "swift-crypto")], resources: [.copy("Fixtures")])
    ]
)
