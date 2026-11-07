import Foundation

enum DiagnosticTransportFailure: Error, Equatable, CustomStringConvertible {
    case deadline, requestLimit, responseInvalid
    case http(Int, String), network(String), priorFailure(String)
    var description: String {
        switch self {
        case .deadline: return "diagnostic deadline exhausted"
        case .requestLimit: return "diagnostic request limit exhausted"
        case .responseInvalid: return "invalid bounded bridge response"
        case let .http(status, reason): return "bridge HTTP \(status): \(reason)"
        case let .network(reason): return "bridge transport failure: \(reason)"
        case let .priorFailure(reason): return "prior bridge failure: \(reason)"
        }
    }
}

struct DiagnosticTransportState {
    var requests = 0
    var deadline = 0.0
    private(set) var firstFailure: DiagnosticTransportFailure?
    static func boundedReason(_ value: String) -> String {
        let safe = String(value.unicodeScalars.filter { $0.value >= 32 && $0.value != 127 })
        var result = String(decoding: safe.utf8.prefix(512), as: UTF8.self)
        while result.utf8.count > 512 { result.removeLast() }
        return result
    }
    mutating func begin(now: Double) throws -> Double {
        if let firstFailure { throw DiagnosticTransportFailure.priorFailure(firstFailure.description) }
        guard requests < 2500 else { throw DiagnosticTransportFailure.requestLimit }
        guard now.isFinite && now < deadline else { throw DiagnosticTransportFailure.deadline }
        requests += 1
        return min(2.0, deadline - now)
    }
    mutating func latch(_ failure: DiagnosticTransportFailure) -> DiagnosticTransportFailure {
        if firstFailure == nil { firstFailure = failure }
        return firstFailure!
    }
    mutating func response(status: Int?, data: Data?, networkError: String?) throws -> [String: Any] {
        if let networkError { throw latch(.network(Self.boundedReason(networkError))) }
        guard let data, data.count <= 8192 else { throw latch(.responseInvalid) }
        let value = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        guard status == 200 else {
            throw latch(.http(status ?? 0, Self.boundedReason(value?["error"] as? String ?? "no bounded reason")))
        }
        guard let value else { throw latch(.responseInvalid) }
        return value
    }
}
