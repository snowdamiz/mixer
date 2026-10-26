// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "AppearanceProbe", targets: [.target(name: "MixerCore"), .target(name: "MixerUI", dependencies: ["MixerCore"]), .executableTarget(name: "Probe", dependencies: ["MixerUI"])])
