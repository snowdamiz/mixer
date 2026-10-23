// swift-tools-version: 6.0
import PackageDescription
let package=Package(name:"UntrustedInjection",platforms:[.macOS(.v14)],dependencies:[.package(path:"../source/sdk")],targets:[.target(name:"UntrustedInjection",dependencies:[.product(name:"MixerCapabilities",package:"sdk")])],swiftLanguageModes:[.v6])
