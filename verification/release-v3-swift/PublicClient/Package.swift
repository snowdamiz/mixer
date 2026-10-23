// swift-tools-version: 6.2
import PackageDescription
let package = Package(name:"MixerReleaseV3PublicClient",platforms:[.macOS(.v14)],
    products:[.executable(name:"v3-proof-client",targets:["proof-client"])],
    dependencies:[.package(path:"../../../updates")],
    targets:[.executableTarget(name:"proof-client",dependencies:[.product(name:"MixerUpdates",package:"updates")])],swiftLanguageModes:[.v6])
