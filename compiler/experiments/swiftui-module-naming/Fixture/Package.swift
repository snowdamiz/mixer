// swift-tools-version: 6.0
import PackageDescription

let apple = Context.environment["S1_APPLE_ALIAS"] == "1"
let shell = apple ? "AppleShell" : "PortableApp"

let package = Package(
    name: "NamingSpike",
    platforms: [.iOS(.v17)],
    products: [.executable(name: shell, targets: [shell])],
    dependencies: [.package(path: "Engine")],
    targets: [
        .target(name: "SharedFeature", dependencies: [
            .product(
                name: "NamingEngine", package: "Engine",
                moduleAliases: apple ? ["SwiftUI": "MixerSwiftUI"] : nil
            ),
        ]),
        .executableTarget(name: shell, dependencies: ["SharedFeature"]),
    ]
)
