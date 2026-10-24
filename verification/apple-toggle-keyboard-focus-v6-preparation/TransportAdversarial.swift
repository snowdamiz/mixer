import Foundation

enum ReviewFailure: Error { case assertion(String) }
enum Checks { nonisolated(unsafe) static var count = 0 }
func check(_ value: Bool, _ label: String) throws {
    Checks.count += 1
    if !value { throw ReviewFailure.assertion(label) }
}
func rejects(_ expected: DiagnosticTransportFailure, _ operation: () throws -> Void) throws {
    do { try operation(); throw ReviewFailure.assertion("Expected \(expected)") }
    catch let actual as DiagnosticTransportFailure { try check(actual == expected, "\(actual) vs \(expected)") }
}

@main struct TransportAdversarial {
    static func main() throws {
        var healthy = DiagnosticTransportState(); healthy.deadline = 29
        try check(try healthy.begin(now: 0) == 2, "request cap")
        try check(try healthy.begin(now: 28.75) == 0.25, "absolute remaining time")
        try check(healthy.deadline == 29 && healthy.requests == 2, "deadline not extended")
        for now in [29.0, 30.0, .infinity, -.infinity, .nan] {
            var expired = DiagnosticTransportState(); expired.deadline = 29
            try rejects(.deadline) { _ = try expired.begin(now: now) }
            try check(expired.requests == 0, "exhausted request not counted")
        }
        var cap = DiagnosticTransportState(); cap.deadline = 29; cap.requests = 2500
        try rejects(.requestLimit) { _ = try cap.begin(now: 1) }
        let body = Data("{\"error\":\"ValueError: Attached Settings geometry\"}".utf8)
        let first = DiagnosticTransportFailure.http(400, "ValueError: Attached Settings geometry")
        var failure = DiagnosticTransportState(); failure.deadline = 29
        try rejects(first) { _ = try failure.response(status: 400, data: body, networkError: nil) }
        try check(failure.firstFailure == first, "first HTTP cause latched")
        failure.requests = 2500
        try rejects(.priorFailure(first.description)) { _ = try failure.begin(now: 100) }
        try rejects(first) { _ = try failure.response(status: 500, data: Data("{}".utf8), networkError: "secondary network error") }
        try rejects(first) { _ = try failure.response(status: 200, data: nil, networkError: nil) }
        try check(failure.firstFailure == first, "secondary capture failure did not replace cause")
        var network = DiagnosticTransportState()
        try rejects(.network("socket lost")) { _ = try network.response(status: nil, data: nil, networkError: "socket lost") }
        try rejects(.network("socket lost")) { _ = try network.response(status: 400, data: body, networkError: nil) }
        for data in [Data("not JSON".utf8), Data("[]".utf8), Data(repeating: 0, count: 8193)] {
            var invalid = DiagnosticTransportState()
            try rejects(.responseInvalid) { _ = try invalid.response(status: 200, data: data, networkError: nil) }
        }
        var noReason = DiagnosticTransportState()
        try rejects(.http(400, "no bounded reason")) { _ = try noReason.response(status: 400, data: Data("bad JSON".utf8), networkError: nil) }
        for text in [String(repeating:"🙂",count:1000), String(repeating:"é",count:1000), String(repeating:"a",count:513), "\u{0}\n\tfirst\r\u{7f}last"] {
            let bounded = DiagnosticTransportState.boundedReason(text)
            try check(bounded.utf8.count <= 512, "reason UTF8 bound")
            try check(bounded.unicodeScalars.allSatisfy { $0.value >= 32 && $0.value != 127 }, "reason controls removed")
        }
        let value = try healthy.response(status:200, data:Data("{\"accepted\":true,\"diagnosticOnly\":true}".utf8), networkError:nil)
        try check(value["accepted"] as? Bool == true && healthy.firstFailure == nil, "success after healthy begin")
        print("{\"status\":\"passed\",\"independentSharedTransportChecks\":\(Checks.count),\"nativeExecuted\":false}")
    }
}
