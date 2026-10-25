// Independently authored host controls. Appended to an exact frozen source prefix.
final class ReviewProtocol: URLProtocol, @unchecked Sendable {
    private static let stateLock = NSLock()
    nonisolated(unsafe) private static var starts = 0
    nonisolated(unsafe) private static var stops = 0
    nonisolated(unsafe) static var expires = false
    static func counts() -> (Int, Int) {
        stateLock.lock(); defer { stateLock.unlock() }; return (starts, stops)
    }
    override class func canInit(with request: URLRequest) -> Bool { request.url?.scheme == "mixerreview" }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.stateLock.lock(); Self.starts += 1; Self.stateLock.unlock()
        if Self.expires { return }
        let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1", headerFields: ["X-Secret": "REVIEW_SECRET_HEADER"])!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Data("{}".utf8))
        client?.urlProtocolDidFinishLoading(self)
    }
    override func stopLoading() { Self.stateLock.lock(); Self.stops += 1; Self.stateLock.unlock() }
}

extension SettingsTelemetry {
    func reviewConfigure(budget: Double) { transport.deadline = now + budget; transport.requests = 9 }
    func reviewPost(_ value: [String: Any]) throws -> [String: Any] {
        lock.lock(); defer { lock.unlock() }; return try post(value)
    }
    func reviewState() -> (Int, DiagnosticTransportFailure?) { (transport.requests, transport.firstFailure) }
}

let selectedControl = CommandLine.arguments[1]
let safeRecord: [String: Any] = ["kind": "chunk", "generation": "12345678-1234-4234-8234-1234567890ab",
    "sequence": 9, "slot": "settings-2500-png", "index": 651, "count": 652,
    "data": "REVIEW_SECRET_BODY", "detail": ["label": "REVIEW_SECRET_DETAIL"], "sha256": "REVIEW_SECRET_HASH"]

if selectedControl == "completed-callback" || selectedControl == "clipped-timeout" {
    precondition(URLProtocol.registerClass(ReviewProtocol.self))
    setenv("MIXER_BRIDGE_URL", "mixerreview://REVIEW_SECRET_HOST", 1)
    setenv("MIXER_BRIDGE_CAPABILITY", "REVIEW_SECRET_CAPABILITY", 1)
    ReviewProtocol.expires = selectedControl == "clipped-timeout"
    let client = SettingsTelemetry()
    client.reviewConfigure(budget: ReviewProtocol.expires ? 0.02 : 2.0)
    if !ReviewProtocol.expires {
        let response = try client.reviewPost(safeRecord)
        precondition(response.isEmpty)
        precondition(client.reviewState().0 == 10 && client.reviewState().1 == nil)
    } else {
        do { _ = try client.reviewPost(safeRecord); fatalError("expected timeout") }
        catch { precondition(error as? DiagnosticTransportFailure == .network("request timeout within existing2second budget")) }
        let original = client.reviewState().1!
        do { _ = try client.reviewPost(["kind": "mark", "stage": "terminal", "sequence": 10]); fatalError("expected prior failure") }
        catch { precondition(error as? DiagnosticTransportFailure == .priorFailure(original.description)) }
        precondition(client.reviewState().0 == 10)
    }
    precondition(ReviewProtocol.counts().0 == 1)
    print("REVIEW_CONTROL {\"case\":\"\(selectedControl)\",\"passed\":true,\"requests\":1}")
}

#if INSTRUMENTED
func parsed(_ line: String) -> [String: Any] {
    precondition(line.hasPrefix("MIXER_SETTINGS_FIRST_FAILURE "))
    precondition(line.utf8.count + 1 <= 2078 && !line.contains("REVIEW_SECRET"))
    return try! JSONSerialization.jsonObject(with: Data(line.dropFirst(29).utf8)) as! [String: Any]
}
let context = SettingsPostFailureContext(requestOrdinal: 10, beginUptime: 100, absoluteDeadlineUptime: 100.012,
    actualAllowanceSeconds: 0.012, taskIdentifier: 99)
if selectedControl == "identity-boundaries" {
    let expectedKeys: Set<String> = ["schema", "kind", "start", "generation", "sequence", "stage", "slot", "chunkIndex", "chunkCount",
        "requestOrdinal", "taskIdentifier", "beginUptime", "endUptime", "absoluteDeadlineUptime", "actualAllowanceSeconds", "overallDeadlineClipped", "branch", "status", "errorCode"]
    var lines: [String] = []
    func inspect(_ value: [String: Any]) -> [String: Any] {
        let diagnostic = SettingsFirstFailureDiagnostic { lines.append($0) }
        diagnostic.record(value, context: context, endUptime: 100.02, branch: .semaphoreExpiration)
        let value = parsed(lines.last!)
        precondition(Set(value.keys) == expectedKeys)
        return value
    }
    let valid = inspect(safeRecord)
    precondition(valid["slot"] as? String == "settings-2500-png" && valid["chunkIndex"] as? Int == 651 && valid["chunkCount"] as? Int == 652)
    precondition(valid["stage"] is NSNull && valid["actualAllowanceSeconds"] as? Double == 0.012 && valid["overallDeadlineClipped"] as? Bool == true)
    for slot in ["settings-0000-ax", "settings-2501-png", "settings-0001-ax\n", "settings-0001-AX", "settings-00001-ax"] {
        var value = safeRecord; value["slot"] = slot
        precondition(inspect(value)["slot"] is NSNull)
    }
    for slot in ["settings-0001-ax", "settings-2500-ax", "settings-0001-png"] {
        var value = safeRecord; value["slot"] = slot
        precondition(inspect(value)["slot"] as? String == slot)
    }
    let badValues: [Any] = [true, 1.0, NSNumber(value: 9), -1, 2501, "9"]
    for bad in badValues {
        var value = safeRecord; value["sequence"] = bad
        precondition(inspect(value)["sequence"] is NSNull)
    }
    var rejected = safeRecord
    rejected["kind"] = "chunk\nREVIEW_SECRET"; rejected["generation"] = String(repeating: "REVIEW_SECRET", count: 1000)
    rejected["stage"] = "REVIEW_SECRET"; rejected["index"] = 652; rejected["count"] = 653
    let redacted = inspect(rejected)
    for key in ["kind", "generation", "stage", "chunkIndex", "chunkCount"] { precondition(redacted[key] is NSNull) }
    print("REVIEW_CONTROL {\"case\":\"identity-boundaries\",\"passed\":true,\"records\":\(lines.count)}")
}
if selectedControl == "sink-failure-before-output" {
    enum ReviewSinkError: Error { case unavailable }
    var calls = 0
    let diagnostic = SettingsFirstFailureDiagnostic { _ in calls += 1; throw ReviewSinkError.unavailable }
    diagnostic.record(safeRecord, context: context, endUptime: 100.02, branch: .semaphoreExpiration)
    diagnostic.record(["kind": "mark", "stage": "terminal", "sequence": 10], context: context, endUptime: 101, branch: .foundationError, errorCode: -999)
    precondition(calls == 1)
    print("REVIEW_CONTROL {\"case\":\"sink-failure-before-output\",\"passed\":true,\"sinkCalls\":1}")
}
if selectedControl == "reentrant-sink" {
    var calls = 0
    var diagnostic: SettingsFirstFailureDiagnostic!
    diagnostic = SettingsFirstFailureDiagnostic { _ in
        calls += 1
        diagnostic.record(["kind": "mark", "stage": "terminal", "sequence": 10], context: context, endUptime: 101, branch: .foundationError)
    }
    diagnostic.record(safeRecord, context: context, endUptime: 100.02, branch: .semaphoreExpiration)
    precondition(calls == 1)
    print("REVIEW_CONTROL {\"case\":\"reentrant-sink\",\"passed\":true,\"sinkCalls\":1}")
}
#endif
