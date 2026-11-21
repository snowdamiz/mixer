@main
struct EpochHost {
    static func main() {
        for argument in CommandLine.arguments.dropFirst() {
            guard let index = Int32(argument) else { fatalError("invalid fixture index") }
            print(epochReadback(index))
        }
    }
}
