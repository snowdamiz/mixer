// swift-tools-version: 6.0
import PackageDescription

// Public source package. Development packages in sdk/, runtime/ and updates/
// remain independently usable; this entry point exports only the owned SDK.
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
        .target(name: "MixerAndroid", dependencies: ["MixerUI"], path: "sdk/Sources/MixerAndroid"),
        .testTarget(name: "MixerAndroidTests", dependencies: ["MixerAndroid", "MixerUI"], path: "sdk/Tests/MixerAndroidTests"),
        .target(name: "MixerCore", path: "sdk/Sources/MixerCore"),
        .target(name: "MixerCapabilityIO", path: "sdk/Sources/MixerCapabilities/NativeIO"),
        .target(name: "MixerCapabilities", dependencies: ["MixerCore", .target(name: "MixerCapabilityIO", condition: .when(platforms: [.iOS, .macOS, .linux, .android]))], path: "sdk/Sources/MixerCapabilities", exclude: ["NativeIO"]),
        .target(name: "MixerUI", dependencies: ["MixerCore"], path: "sdk/Sources/MixerUI"),
        .target(name: "MixerSwiftUI", dependencies: ["MixerUI"], path: "sdk/Sources/MixerSwiftUI"),
        .target(name: "MixerGuest", dependencies: ["MixerCore", "MixerUI", .product(name: "Crypto", package: "swift-crypto", condition: .when(platforms: [.macOS, .iOS, .linux, .android]))], path: "sdk/Sources/MixerGuest"),
        .testTarget(name: "MixerCoreTests", dependencies: ["MixerCore"], path: "sdk/Tests/MixerCoreTests"),
        .testTarget(name: "MixerUITests", dependencies: ["MixerCore", "MixerUI", "MixerGuest"], path: "sdk/Tests/MixerUITests"),
    ],
    swiftLanguageModes: [.v6]
)
// Package conditions follow the manifest host; cross-compilers on macOS must select a portable product.
#if os(macOS)
package.products.append(
.library(name: "MixerApple", targets: ["MixerApple"])
)
package.targets.append(
.target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI", "MixerSwiftUI"], path: "sdk/Sources/MixerApple")
)
package.targets.append(
.testTarget(name: "MixerAppleTests", dependencies: ["MixerApple", "MixerUI"], path: "sdk/Tests/MixerAppleTests")
)
#endif
