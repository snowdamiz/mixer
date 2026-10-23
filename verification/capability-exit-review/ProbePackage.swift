// swift-tools-version: 6.0
import PackageDescription
let package=Package(name:"IndependentExitReview",platforms:[.macOS(.v14)],dependencies:[.package(path:"../source/sdk")],targets:[.testTarget(name:"IndependentExitProbe",dependencies:[.product(name:"MixerCapabilities",package:"sdk")])],swiftLanguageModes:[.v6])
