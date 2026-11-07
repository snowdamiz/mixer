import Foundation

/// Local-only, bounded metadata. Never retain or emit URL, headers, response text,
/// snapshot/detail dictionaries, capability values, hashes, or payload bytes.
struct SettingsPostFailureContext {
    let requestOrdinal: Int
    let beginUptime: Double
    let absoluteDeadlineUptime: Double
    var actualAllowanceSeconds: Double?
    var taskIdentifier: Int?
}

enum SettingsPostFailureBranch: String {
    case beginDeadline = "begin-deadline"
    case beginRequestLimit = "begin-request-limit"
    case beginPriorFailure = "begin-prior-failure"
    case configuration, serialization
    case bodyLimit = "body-limit"
    case semaphoreExpiration = "semaphore-expiration"
    case foundationError = "foundation-error"
    case httpRejection = "http-rejection"
    case invalidResponse = "invalid-response"
}

/// This latch is independent of, and cannot replace, DiagnosticTransportState's
/// original failure. Select one record under a lock; never call into the bridge.
final class SettingsFirstFailureDiagnostic: @unchecked Sendable {
    private let lock = NSLock()
    private var selected = false
    private let emit: (String) throws -> Void
    init(emit: @escaping (String) throws -> Void = { print($0) }) { self.emit = emit }

    private static func integer(_ value: Any?, range: ClosedRange<Int>) -> Int? {
        guard let value, type(of: value) == Int.self, let result = value as? Int,
              range.contains(result) else { return nil }
        return result
    }
    private static func generation(_ value: Any?) -> String? {
        guard let value = value as? String, value.utf8.count == 36,
              let uuid = UUID(uuidString: value), uuid.uuidString.lowercased() == value.lowercased() else { return nil }
        return value
    }
    private static func slot(_ value: Any?) -> String? {
        guard let value = value as? String, value.utf8.count == 16 || value.utf8.count == 17 else { return nil }
        let parts = value.split(separator: "-", omittingEmptySubsequences: false)
        guard parts.count == 3, parts[0] == "settings", parts[1].utf8.count == 4,
              parts[1].utf8.allSatisfy({ (48...57).contains($0) }),
              let number = Int(parts[1]), (1...2500).contains(number),
              parts[2] == "ax" || parts[2] == "png" else { return nil }
        return value
    }
    func record(_ record: [String: Any], context: SettingsPostFailureContext,
                endUptime: Double, branch: SettingsPostFailureBranch,
                status: Int? = nil, errorCode: Int? = nil) {
        lock.lock()
        guard !selected else { lock.unlock(); return }
        selected = true
        lock.unlock()
        // Diagnostics are ancillary: every failure here is swallowed after the
        // first selection, so it cannot replace the original error or retry.
        let kinds = ["start", "mark", "observe", "chunk"]
        let stages = ["settings-launched", "route-tap", "switch-action", "terminate-before", "terminate-after",
                      "test-case-finished", "suite-finished", "bundle-finished", "route-search", "route-opened",
                      "before-switch", "after-switch", "poll", "terminal"]
        let kind = (record["kind"] as? String).flatMap { kinds.contains($0) ? $0 : nil }
        let stage = (record["stage"] as? String).flatMap { stages.contains($0) ? $0 : nil }
        func number(_ value: Double?) -> Any { value.flatMap { $0.isFinite ? $0 : nil }.map { $0 as Any } ?? NSNull() }
        let values: [String: Any] = [
            "schema": 1, "kind": kind as Any? ?? NSNull(), "start": kind == "start",
            "generation": Self.generation(record["generation"]) as Any? ?? NSNull(),
            "sequence": (kind == "start" ? 0 : Self.integer(record["sequence"], range: 1...2500)) as Any? ?? NSNull(),
            "stage": stage as Any? ?? NSNull(), "slot": Self.slot(record["slot"]) as Any? ?? NSNull(),
            "chunkIndex": Self.integer(record["index"], range: 0...651) as Any? ?? NSNull(),
            "chunkCount": Self.integer(record["count"], range: 1...652) as Any? ?? NSNull(),
            "requestOrdinal": context.requestOrdinal, "taskIdentifier": context.taskIdentifier as Any? ?? NSNull(),
            "beginUptime": number(context.beginUptime), "endUptime": number(endUptime),
            "absoluteDeadlineUptime": number(context.absoluteDeadlineUptime),
            "actualAllowanceSeconds": number(context.actualAllowanceSeconds),
            "overallDeadlineClipped": context.actualAllowanceSeconds.map { $0 < 2.0 } as Any? ?? NSNull(),
            "branch": branch.rawValue, "status": status as Any? ?? NSNull(), "errorCode": errorCode as Any? ?? NSNull()
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: values, options: [.sortedKeys]),
              data.count <= 2048, let json = String(data: data, encoding: .utf8) else { return }
        try? emit("MIXER_SETTINGS_FIRST_FAILURE " + json)
    }
}
