// swift-tools-version: 6.0
import PackageDescription

// Development integration only. The consumer supplies its admitted libmixer_vm.a
// through its explicit library search path. This package never builds/downloads it.
let package = Package(
    name: "MixerNativeBackend",
    platforms: [.macOS(.v14), .iOS("17.0")],
    products: [.library(name: "MixerNativeBackend", targets: ["MixerNativeBackend"])],
    dependencies: [.package(path: "../sdk")],
    targets: [
        .systemLibrary(name: "CMixerVM"),
        .target(name: "MixerNativeBackend", dependencies: [.product(name: "MixerGuest", package: "sdk"), "CMixerVM"])
    ],
    swiftLanguageModes: [.v6]
)
