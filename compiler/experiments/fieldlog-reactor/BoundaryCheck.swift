// Native executable check of the same boundary linked into the reactor.
enum DeliberateFailure: Error { case expected }

@main
struct BoundaryCheck {
    static func main() {
        var invocations = 0
        precondition(fieldLogStatus { invocations += 1; throw DeliberateFailure.expected } == 1)
        precondition(invocations == 1)
        precondition(fieldLogStatus { invocations += 1 } == 0)
        precondition(invocations == 2)
        precondition(mixerFieldLogCorpusV1() == 0)
        precondition(mixerFieldLogCorpusV1() == 0)
    }
}
