// swift-tools-version: 6.0
import PackageDescription
let package = Package(name: "DescriptorProposalProbe", platforms: [.macOS(.v14)], targets: [
    .target(name: "MixerCore"), .target(name: "MixerUI", dependencies: ["MixerCore"]),
    .executableTarget(name: "DescriptorProbe", dependencies: ["MixerUI"])], swiftLanguageModes: [.v6])
