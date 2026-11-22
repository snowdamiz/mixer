// swift-tools-version: 6.2
import PackageDescription

let package = Package(
  name: "FieldLogAssignmentHost",
  platforms: [.macOS(.v14)],
  dependencies: [
    .package(path: "../fieldlog"),
    .package(path: "../mixer/sdk"),
    .package(path: "../mixer/capability-activation"),
    .package(path: "../mixer/runtime-identity"),
  ],
  targets: [
    .executableTarget(name: "AssignmentHost", dependencies: [
      .product(name: "FieldLogModels", package: "fieldlog"),
      .product(name: "FieldLogStorage", package: "fieldlog"),
      .product(name: "FieldLogFeatures", package: "fieldlog"),
      .product(name: "FieldLogEntrySaving", package: "fieldlog"),
      .product(name: "MixerCapabilities", package: "sdk"),
      .product(name: "MixerCapabilityActivation", package: "capability-activation"),
      .product(name: "MixerRuntimeIdentity", package: "runtime-identity"),
    ]),
  ]
)
