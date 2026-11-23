// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "NamingEngine",
    platforms: [.iOS(.v17)],
    products: [.library(name: "NamingEngine", targets: ["SwiftUI"])],
    targets: [
        .target(name: "TitleSupport"),
        .target(name: "SwiftUI", dependencies: ["TitleSupport"]),
    ]
)
