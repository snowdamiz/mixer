// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "MixerActivation", platforms: [.iOS(.v17), .macOS(.v14)],
    products: [.library(name: "MixerActivation", targets: ["MixerActivation"])],
    dependencies: [
        .package(path: "../runtime"), .package(path: "../updates"),
        .package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3"),
    ],
    targets: [
        .target(name: "MixerActivation", dependencies: [
            .product(name: "MixerRuntime", package: "runtime"),
            .product(name: "MixerUpdates", package: "updates"),
        ]),
        .testTarget(name: "MixerActivationTests", dependencies: [
            "MixerActivation", .product(name: "Crypto", package: "swift-crypto"),
        ]),
    ],
    swiftLanguageModes: [.v6]
)
