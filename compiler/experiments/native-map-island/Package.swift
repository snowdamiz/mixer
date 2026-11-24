// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "NativeMapIslandExperiment",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../../../sdk"),
        .package(path: "../../../updates"),
    ],
    targets: [
        .executableTarget(name: "NativeMapReplay", dependencies: [
            .product(name: "MixerUI", package: "sdk"),
            .product(name: "MixerUpdates", package: "updates"),
        ]),
    ]
)
