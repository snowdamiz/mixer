import Foundation

enum HostFailure: Error { case assertion(String) }
enum CheckCount { nonisolated(unsafe) static var value = 0 }
func check(_ value: Bool, _ name: String) throws { CheckCount.value += 1; if !value { throw HostFailure.assertion(name) } }
func fails(_ expected: DiagnosticTransportFailure, _ body: () throws -> Void) throws {
    do { try body(); throw HostFailure.assertion("expected failure \(expected)") }
    catch let actual as DiagnosticTransportFailure { try check(actual == expected, "cause \(actual) != \(expected)") }
}
@main struct TransportControls {
    static func main() throws {
        var state = DiagnosticTransportState(); state.deadline = 29
        try check(try state.begin(now: 1) == 2, "request2second cap")
        try check(state.requests == 1 && state.deadline == 29, "no deadline reset")
        try check(try state.begin(now: 28.5) == 0.5, "remaining absolute budget")
        var expired = DiagnosticTransportState(); expired.deadline = 29
        try fails(.deadline) { _ = try expired.begin(now: 29) }
        try fails(.deadline) { _ = try expired.begin(now: .nan) }
        expired.requests = 2500
        try fails(.requestLimit) { _ = try expired.begin(now: 1) }
        var rejected = DiagnosticTransportState(); rejected.deadline = 29
        let body = Data("{\"error\":\"ValueError: Attached Settings geometry\"}".utf8)
        let cause = DiagnosticTransportFailure.http(400, "ValueError: Attached Settings geometry")
        try fails(cause) { _ = try rejected.response(status: 400, data: body, networkError: nil) }
        try check(rejected.firstFailure == cause, "first HTTP rejection retained")
        rejected.requests = 2500
        try fails(.priorFailure(cause.description)) { _ = try rejected.begin(now: 100) }
        try fails(cause) { _ = try rejected.response(status: 500, data: Data("{}".utf8), networkError: "secondary") }
        var network = DiagnosticTransportState()
        try fails(.network("connection lost")) { _ = try network.response(status: nil, data: nil, networkError: "connection lost") }
        var invalid = DiagnosticTransportState()
        try fails(.responseInvalid) { _ = try invalid.response(status: 200, data: Data(repeating: 0, count: 8193), networkError: nil) }
        var malformed = DiagnosticTransportState()
        try fails(.responseInvalid) { _ = try malformed.response(status: 200, data: Data("invalid".utf8), networkError: nil) }
        var unknown = DiagnosticTransportState()
        try fails(.http(0, "no bounded reason")) { _ = try unknown.response(status: nil, data: Data("{}".utf8), networkError: nil) }
        let reason = DiagnosticTransportState.boundedReason(String(repeating: "🙂", count: 1000) + "\n\u{0}")
        try check(reason.utf8.count <= 512 && !reason.contains("\n") && !reason.contains("\0"), "bounded single-line reason")
        var healthy = DiagnosticTransportState()
        let value = try healthy.response(status: 200, data: Data("{\"accepted\":true}".utf8), networkError: nil)
        try check(value["accepted"] as? Bool == true && healthy.firstFailure == nil, "successful response")
        print("{\"status\":\"passed\",\"sharedSwiftTransportChecks\":\(CheckCount.value),\"nativeExecuted\":false}")
    }
}
