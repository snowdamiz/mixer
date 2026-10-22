// swift-tools-version: 6.0
import PackageDescription

let package = Package(
  name: "MixerAndroidEngine", platforms: [.macOS(.v14)],
  products: [.library(name: "MixerAndroidEngine", type: .dynamic, targets: ["MixerAndroidEngine"])],
  dependencies: [.package(path: "../../../sdk")],
  targets: [
    .target(name: "MixerAndroidEngine", dependencies: [.product(name: "MixerUI", package: "sdk")]),
    .testTarget(name: "MixerAndroidEngineTests", dependencies: ["MixerAndroidEngine"]),
  ], swiftLanguageModes: [.v6])
