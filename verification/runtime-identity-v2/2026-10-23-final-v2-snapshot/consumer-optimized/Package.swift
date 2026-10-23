// swift-tools-version: 6.2
import PackageDescription
let package = Package(name:"Identity2Consumer", platforms:[.macOS(.v14)], dependencies:[.package(path:"/Users/andreyyurlov/Documents/dev/mixer/verification/runtime-identity-v2/local/final-v2-snapshot/source/runtime-identity")], targets:[.executableTarget(name:"Consumer",dependencies:[.product(name:"MixerRuntimeIdentity",package:"runtime-identity")])])
