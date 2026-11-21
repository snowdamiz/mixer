@main
struct PresentationHost {
    static func main() {
        for argument in CommandLine.arguments.dropFirst() {
            guard let index = Int32(argument) else { fatalError("invalid fixture index") }
            print(presentationReadback(index))
        }
    }
}
