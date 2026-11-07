// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "MixerAndroidEngine", platforms: [.macOS(.v14)],
  products: [.library(name: "MixerAndroidEngine", type: .dynamic, targets: ["MixerAndroidEngine"]),
    .library(name: "MixerAndroidRuntime", targets: ["MixerAndroidRuntime"])],
  dependencies: [.package(path: "../../../sdk")],
  targets: [
    .target(name: "MixerAndroidRuntime", dependencies: [.product(name: "MixerCore", package: "sdk"), .product(name: "MixerUI", package: "sdk")]),
    .target(name: "MixerAndroidEngine", dependencies: ["MixerAndroidRuntime", .product(name: "MixerUI", package: "sdk")]),
    .testTarget(name: "MixerAndroidEngineTests", dependencies: ["MixerAndroidEngine"]),
    .testTarget(name: "MixerAndroidRuntimeTests", dependencies: ["MixerAndroidRuntime", .product(name: "MixerUI", package: "sdk")]),
  ], swiftLanguageModes: [.v6])
