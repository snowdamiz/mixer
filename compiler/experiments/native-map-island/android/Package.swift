// swift-tools-version: 6.2
import PackageDescription

let package = Package(
    name: "GC3AndroidMapFixture",
    platforms: [.macOS(.v14)],
    products: [.library(name: "GC3MapAdmission", type: .dynamic, targets: ["MapAdmission"])],
    dependencies: [.package(path: "../../../../updates")],
    targets: [
        .systemLibrary(name: "CGC3"),
        .target(name: "MapAdmission", dependencies: [
            "CGC3", .product(name: "MixerUpdates", package: "updates"),
        ]),
    ]
)
