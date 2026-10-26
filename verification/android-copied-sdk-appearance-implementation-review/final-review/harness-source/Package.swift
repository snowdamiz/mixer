// swift-tools-version: 6.0
import PackageDescription
let package = Package(name:"IndependentAndroidReview",platforms:[.macOS(.v14)],dependencies:[.package(path:"../candidate/sdk")],targets:[.executableTarget(name:"ReviewDriver",dependencies:[.product(name:"MixerUI",package:"sdk")],resources:[.copy("Resources")])])
