// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "FieldLogEditorControl",
  platforms: [.macOS(.v14)],
  targets: [
    .executableTarget(name: "AXProbe", dependencies: ["FieldLogFeatures", "MixerUI", "MixerApple"],
                      path: "AXProbe"),
    .target(name: "MixerCore", path: "mixer/sdk/Sources/MixerCore"),
    .target(name: "MixerUI", dependencies: ["MixerCore"], path: "mixer/sdk/Sources/MixerUI"),
    .target(name: "MixerApple", dependencies: ["MixerCore", "MixerUI"], path: "mixer/sdk/Sources/MixerApple"),
    .target(name: "FieldLogModels", path: "fieldlog/Sources/FieldLogModels"),
    .target(name: "FieldLogStorage", dependencies: ["FieldLogModels"], path: "fieldlog/Sources/FieldLogStorage"),
    .target(name: "FieldLogFeatures",
            dependencies: ["FieldLogModels", "MixerCore", "MixerUI", "MixerApple"],
            path: "fieldlog/Sources/FieldLogFeatures"),
    .testTarget(name: "FieldLogTests",
                dependencies: ["FieldLogModels", "FieldLogStorage", "FieldLogFeatures", "MixerUI", "MixerApple"],
                path: "fieldlog/Tests/FieldLogTests"),
  ]
)
