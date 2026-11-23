// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Mixer",
    platforms: [.iOS("17.0"), .macOS(.v14)],
    products: [
        .library(name: "MixerCore", targets: ["MixerCore"]),
        .library(name: "MixerAndroid", targets: ["MixerAndroid"]),
        .library(name: "MixerUI", targets: ["MixerUI"]),
        .library(name: "MixerSwiftUI", targets: ["MixerSwiftUI"]),
        .library(name: "MixerGuest", targets: ["MixerGuest"]),
        .library(name: "MixerCapabilities", targets: ["MixerCapabilities"]),
    ],
    dependencies: [.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")],
    targets: [
        .target(name: "MixerAndroid", dependencies: ["MixerUI"], path: "Sources/MixerAndroid"),
        .testTarget(name: "MixerAndroidTests", dependencies: ["MixerAndroid", "MixerUI"], path: "Tests/MixerAndroidTests"),
        .target(name: "MixerCore"),
        .target(name: "MixerCapabilityIO", path: "Sources/MixerCapabilities/NativeIO"),
        .target(name: "MixerCapabilities", dependencies: ["MixerCore", .target(name: "MixerCapabilityIO", condition: .when(platforms: [.iOS, .macOS, .linux, .android]))], exclude: ["NativeIO"]),
        .target(name: "MixerUI", dependencies: ["MixerCore"]),
        .target(name: "MixerSwiftUI", dependencies: ["MixerUI"]),
        .target(name: "MixerGuest", dependencies: ["MixerCore", "MixerUI", .product(name: "Crypto", package: "swift-crypto", condition: .when(platforms: [.macOS, .iOS, .linux, .android]))]),
        .testTarget(name: "MixerCoreTests", dependencies: ["MixerCore"]),
        .testTarget(name: "MixerUITests", dependencies: ["MixerCore", "MixerUI", "MixerGuest"]),
    ],
    swiftLanguageModes: [.v6]
)

#if os(macOS)
// Manifests run on the host. Cross-builds must select a destination-compatible product.
package.products.append(.library(name: "MixerApple", targets: ["MixerApple"]))
package.targets += [
    .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI"]),
    .testTarget(name: "MixerAppleTests", dependencies: ["MixerApple", "MixerUI"]),
]
#endif
