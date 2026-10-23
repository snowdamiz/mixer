// swift-tools-version: 6.2
import PackageDescription
let package = Package(name: "IndependentUIReview", platforms: [.macOS(.v14)], dependencies: [.package(path: "/Users/andreyyurlov/Documents/dev/mixer/.build/guest-ui-presentation/sdk")], targets: [.target(name: "MixerCapabilityActivation", dependencies: [.product(name: "MixerGuest", package: "sdk"), .product(name: "MixerUI", package: "sdk"), .product(name: "MixerApple", package: "sdk")]), .testTarget(name: "ReviewTests", dependencies: ["MixerCapabilityActivation", .product(name: "MixerGuest", package: "sdk")])], swiftLanguageModes: [.v6])
