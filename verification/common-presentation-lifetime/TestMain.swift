import Testing

@main
struct PresentationTestMain {
    static func main() async {
        let code: CInt = await Testing.__swiftPMEntryPoint()
        if code != 0 { fatalError("Swift Testing returned \(code)") }
    }
}
