// Appended to the exact derivative SettingsTelemetry prefix by run_controls.py.
// Custom URLProtocol scheme cannot reach a socket, even if interception fails.
final class HostProtocol: URLProtocol, @unchecked Sendable {
    enum Mode { case success, foundationError, httpRejection, invalidJSON, missingData, oversized, timeout }
    private static let guardLock = NSLock()
    nonisolated(unsafe) private static var mode: Mode = .success
    nonisolated(unsafe) private static var started = 0
    nonisolated(unsafe) private static var stopped = 0
    static func configure(_ value: Mode) { guardLock.lock(); mode = value; started = 0; stopped = 0; guardLock.unlock() }
    static func counts() -> (Int, Int) { guardLock.lock(); defer { guardLock.unlock() }; return (started, stopped) }
    override class func canInit(with request: URLRequest) -> Bool { request.url?.scheme == "mixerhostcontrol" }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        Self.guardLock.lock(); let mode = Self.mode; Self.started += 1; Self.guardLock.unlock()
        switch mode {
        case .timeout: return
        case .foundationError:
            client?.urlProtocol(self, didFailWithError: NSError(domain: NSURLErrorDomain, code: -1001, userInfo: [NSLocalizedDescriptionKey: "SECRET_ERROR_PAYLOAD"]))
        default:
            let status = mode == .httpRejection ? 503 : 200
            let response = HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: nil)!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            let payload: Data
            switch mode {
            case .invalidJSON: payload = Data("SECRET_INVALID_RESPONSE".utf8)
            case .missingData: payload = Data()
            case .oversized: payload = Data(repeating: 65, count: 8193)
            case .httpRejection: payload = Data("{\"error\":\"SECRET_SERVER_REASON\"}".utf8)
            default: payload = Data("{\"ok\":true}".utf8)
            }
            client?.urlProtocol(self, didLoad: payload)
            client?.urlProtocolDidFinishLoading(self)
        }
    }
    override func stopLoading() { Self.guardLock.lock(); Self.stopped += 1; Self.guardLock.unlock() }
}

extension SettingsTelemetry {
    func controlConfigure(_ budget: Double, requests: Int = 0) {
        lock.lock(); defer { lock.unlock() }
        transport.deadline = now + budget; transport.requests = requests
    }
    func controlPost(_ record: [String: Any]) throws -> [String: Any] {
        lock.lock(); defer { lock.unlock() }; return try post(record)
    }
    func controlState() -> (Int, DiagnosticTransportFailure?) {
        lock.lock(); defer { lock.unlock() }; return (transport.requests, transport.firstFailure)
    }
}

final class Lines: @unchecked Sendable {
    private let lock = NSLock()
    private var lines: [String] = []
    func append(_ line: String) { lock.lock(); lines.append(line); lock.unlock() }
    func snapshot() -> [String] { lock.lock(); defer { lock.unlock() }; return lines }
}

enum SinkFailure: Error { case synthetic }
let mode = CommandLine.arguments[1]
let record: [String: Any] = ["kind": "chunk", "generation": "12345678-1234-4234-8234-1234567890ab", "sequence": 221,
                           "slot": "settings-0195-png", "index": 21, "count": 71,
                           "data": "SECRET_PNG_AX_PAYLOAD", "snapshot": ["label": "SECRET_AX_LABEL"],
                           "detail": ["secret": "SECRET_DETAIL"], "capability": "SECRET_RECORD_CAPABILITY"]
setenv("MIXER_BRIDGE_URL", "mixerhostcontrol://SECRET_URL_HOST", 1)
setenv("MIXER_BRIDGE_CAPABILITY", "SECRET_HEADER_CAPABILITY", 1)
precondition(URLProtocol.registerClass(HostProtocol.self))
private let telemetry = SettingsTelemetry()
var result: [String: Any] = ["case": mode]
func failPost(_ value: [String: Any] = record) -> Error {
    do { _ = try telemetry.controlPost(value); fatalError("expected original failure") }
    catch { return error }
}
switch mode {
case "success":
    HostProtocol.configure(.success); telemetry.controlConfigure(29)
    let reply = try telemetry.controlPost(record)
    precondition(reply["ok"] as? Bool == true)
    precondition(telemetry.controlState().0 == 1 && telemetry.controlState().1 == nil)
case "deadline":
    HostProtocol.configure(.success); telemetry.controlConfigure(-1)
    precondition(failPost() as? DiagnosticTransportFailure == .deadline)
    precondition(telemetry.controlState().0 == 0 && telemetry.controlState().1 == nil)
case "request-limit":
    HostProtocol.configure(.success); telemetry.controlConfigure(29, requests: 2500)
    precondition(failPost() as? DiagnosticTransportFailure == .requestLimit)
    precondition(telemetry.controlState().0 == 2500 && telemetry.controlState().1 == nil)
case "timeout":
    HostProtocol.configure(.timeout); telemetry.controlConfigure(0.025)
    let first = failPost() as! DiagnosticTransportFailure
    precondition(first == .network("request timeout within existing2second budget"))
    precondition(telemetry.controlState().1 == first)
    precondition(failPost() as? DiagnosticTransportFailure == .priorFailure(first.description))
    precondition(telemetry.controlState().0 == 1)
case "foundation-error", "http-rejection", "invalid-response", "oversized-response", "empty-response":
    let kind: HostProtocol.Mode = mode == "foundation-error" ? .foundationError : mode == "http-rejection" ? .httpRejection : mode == "oversized-response" ? .oversized : mode == "empty-response" ? .missingData : .invalidJSON
    HostProtocol.configure(kind); telemetry.controlConfigure(29)
    let first = failPost() as! DiagnosticTransportFailure
    switch first {
    case .network(let reason): precondition(mode == "foundation-error" && reason.contains("SECRET_ERROR_PAYLOAD"))
    case .http(let status, let reason): precondition(mode == "http-rejection" && status == 503 && reason == "SECRET_SERVER_REASON")
    case .responseInvalid: precondition(["invalid-response", "oversized-response", "empty-response"].contains(mode))
    default: fatalError("wrong original failure")
    }
    precondition(telemetry.controlState().1 == first)
    precondition(failPost() as? DiagnosticTransportFailure == .priorFailure(first.description))
    precondition(telemetry.controlState().0 == 1)
case "body-limit":
    HostProtocol.configure(.success); telemetry.controlConfigure(29)
    var value = record; value["data"] = String(repeating: "SECRET_BODY", count: 1000)
    guard case SettingsTelemetry.Failure.upload = failPost(value) else { fatalError("wrong original body failure") }
    precondition(telemetry.controlState().0 == 1 && telemetry.controlState().1 == nil)
case "configuration":
    HostProtocol.configure(.success); telemetry.controlConfigure(29); unsetenv("MIXER_BRIDGE_CAPABILITY")
    guard case SettingsTelemetry.Failure.bridge = failPost() else { fatalError("wrong original configuration failure") }
    precondition(telemetry.controlState().0 == 1 && telemetry.controlState().1 == nil)
case "serialization":
    HostProtocol.configure(.success); telemetry.controlConfigure(29)
    var value = record; value["unsupported"] = Double.nan
    let first = failPost(value) as NSError
    precondition(first.domain == NSCocoaErrorDomain && first.code == 3840)
    precondition(telemetry.controlState().0 == 1 && telemetry.controlState().1 == nil)
case "metadata-redaction", "sink-failure", "concurrency", "nonfinite", "start-identity", "mark-identity":
    let lines = Lines()
    let diagnostic = SettingsFirstFailureDiagnostic { line in lines.append(line); if mode == "sink-failure" { throw SinkFailure.synthetic } }
    let context = SettingsPostFailureContext(requestOrdinal: 222, beginUptime: 100, absoluteDeadlineUptime: 100.012,
                                             actualAllowanceSeconds: 0.012, taskIdentifier: 221)
    var value = record
    if mode == "metadata-redaction" {
        value["kind"] = "SECRET_KIND"; value["generation"] = "SECRET_GENERATION"; value["sequence"] = true
        value["stage"] = "SECRET_STAGE"; value["slot"] = "settings-SECRET-png"; value["index"] = -1; value["count"] = 99999
    } else if mode == "start-identity" { value = ["kind": "start", "case": "SECRET_CASE", "uptime": 100.0] }
    else if mode == "mark-identity" { value = ["kind": "mark", "generation": record["generation"]!, "sequence": 118, "stage": "switch-action", "detail": ["label": "SECRET_AX_LABEL"]] }
    if mode == "concurrency" {
        DispatchQueue.concurrentPerform(iterations: 128) { _ in diagnostic.record(value, context: context, endUptime: 100.02, branch: .semaphoreExpiration) }
    } else if mode == "nonfinite" {
        diagnostic.record(value, context: SettingsPostFailureContext(requestOrdinal: 1, beginUptime: .nan, absoluteDeadlineUptime: .infinity), endUptime: -.infinity, branch: .beginDeadline)
    } else { diagnostic.record(value, context: context, endUptime: 100.02, branch: .semaphoreExpiration) }
    diagnostic.record(record, context: context, endUptime: 101, branch: .foundationError, errorCode: -999)
    precondition(lines.snapshot().count == 1)
    precondition(!lines.snapshot()[0].contains("SECRET"))
    print(lines.snapshot()[0])
    result["concurrentAttempts"] = mode == "concurrency" ? 128 : 0
case "budget-controls":
    var ample = DiagnosticTransportState(); ample.deadline = 129
    let ceiling = try ample.begin(now: 100)
    precondition(ceiling == 2)
    var clipped = DiagnosticTransportState(); clipped.deadline = 939365.989950875 + 29
    let allowance = try clipped.begin(now: 939394.9777934167)
    precondition(abs(allowance - 0.01215745834633708) < 0.000000001)
    result["exampleAllowanceSeconds"] = allowance
    let lines = Lines(); let diagnostic = SettingsFirstFailureDiagnostic { lines.append($0) }
    diagnostic.record(record, context: SettingsPostFailureContext(requestOrdinal: 222, beginUptime: 939394.9777934167,
        absoluteDeadlineUptime: clipped.deadline, actualAllowanceSeconds: allowance, taskIdentifier: 221), endUptime: 939394.99, branch: .semaphoreExpiration)
    print(lines.snapshot()[0])
default: fatalError("unknown control")
}
let counts = HostProtocol.counts()
result["protocolRequests"] = counts.0; result["passed"] = true
print("HOST_CONTROL " + String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
