import Foundation

// Diagnostic data only. No UIKit, timers, input, oracle, or release authority.
enum PassiveLifecycleSite: String, CaseIterable, Sendable { case registration, snapshot, controllerCallback = "controller-callback", carrierCallback = "carrier-callback", notification }
enum PassiveLifecycleKind: String, CaseIterable, Sendable {
    case appActive = "app-did-become-active", appInactive = "app-will-resign-active", appForeground = "app-will-enter-foreground", appBackground = "app-did-enter-background"
    case windowKey = "window-did-become-key", windowNotKey = "window-did-resign-key", windowVisible = "window-did-become-visible", windowHidden = "window-did-become-hidden"
    case sceneConnect = "scene-will-connect", sceneDisconnect = "scene-did-disconnect", sceneActive = "scene-did-activate", sceneInactive = "scene-will-deactivate", sceneForeground = "scene-will-enter-foreground", sceneBackground = "scene-did-enter-background"
    var family: Int {
        switch self {
        case .appActive, .appInactive, .appForeground, .appBackground: return 0
        case .windowKey, .windowNotKey, .windowVisible, .windowHidden: return 1
        default: return 2
        }
    }
}
enum PassiveLifecycleAppState: String, CaseIterable, Sendable { case active, inactive, background, unknown }
enum PassiveLifecycleSceneState: String, CaseIterable, Sendable { case absent, unattached, foregroundActive = "foreground-active", foregroundInactive = "foreground-inactive", background, unknown }
enum PassiveLifecycleRegistration: String, CaseIterable, Sendable { case notRegistered = "not-registered", registered, invalid = "incomplete-registration", stopped }
enum PassiveLifecycleIssue: String, CaseIterable, Sendable {
    case count = "incomplete-count", bytes = "incomplete-bytes", counter = "incomplete-counter", timing = "incomplete-time", data = "incomplete-data", thread = "incomplete-thread", ownership = "incomplete-ownership", registration = "incomplete-registration"
}

struct PassiveLifecycleIdentity {
    let value: String
    init(_ object: AnyObject) { value = "0x" + String(UInt(bitPattern: Unmanaged.passUnretained(object).toOpaque()), radix: 16) }
}

// Weak references and identity comparisons shared with the host tests. The
// adapter supplies only window.windowScene, never a scene found by enumeration.
final class PassiveLifecycleOwnership {
    weak var application: AnyObject?
    weak var window: AnyObject?
    init(application: AnyObject, window: AnyObject) { self.application = application; self.window = window }
    func accepts(_ kind: PassiveLifecycleKind, object: AnyObject?, currentScene: AnyObject?) -> Bool {
        guard let application, let window, let object else { return false }
        switch kind.family {
        case 0: return object === application
        case 1: return object === window
        default: return currentScene != nil && object === currentScene
        }
    }
}

// NotificationCenter keeps its block tokens. Their blocks retain only the fault
// counter and weak observer. Removing/deinitializing this bag unregisters all 14.
final class PassiveLifecycleTokens {
    private let center: NotificationCenter
    private var tokens: [NSObjectProtocol] = []
    init(center: NotificationCenter) { self.center = center }
    var count: Int { tokens.count }
    func insert(_ token: NSObjectProtocol) -> Bool {
        guard tokens.count < PassiveLifecycleKind.allCases.count else { center.removeObserver(token); return false }
        tokens.append(token); return true
    }
    func removeAll() { for token in tokens { center.removeObserver(token) }; tokens.removeAll() }
    deinit { removeAll() }
}

// Off-main delivery never schedules a later snapshot or touches actor state.
// It records only a saturating fault count, merged into the next exported value.
final class PassiveLifecycleDeliveryFaults: @unchecked Sendable {
    private let lock = NSLock()
    private var count = 0
    func record() { lock.lock(); defer { lock.unlock() }; if count < PassiveLifecycleBuffer.counterLimit { count += 1 } }
    var value: Int { lock.lock(); defer { lock.unlock() }; return count }
}

struct PassiveLifecycleSnapshot {
    let systemUptime: Double
    let finishedUptime: Double
    let processIdentifier: Int
    let site: PassiveLifecycleSite
    let contextSequence: Int?
    let notificationKind: PassiveLifecycleKind?
    let notificationObjectIdentity: PassiveLifecycleIdentity?
    let applicationState: PassiveLifecycleAppState
    let ownedWindowIdentity: PassiveLifecycleIdentity?
    let ownedWindowIsKey: Bool?
    let ownedWindowSceneIdentity: PassiveLifecycleIdentity?
    let ownedSceneActivationState: PassiveLifecycleSceneState
}

// Only the main-actor adapter mutates this buffer in the app. Host tests use the
// same actual row validation, counters, envelope, reservation and serialization.
final class PassiveLifecycleBuffer {
    static let maximumRows = 64
    static let columns = ["sequence", "systemUptime", "finishedUptime", "processIdentifier", "site", "contextSequence", "notificationKind", "notificationObjectIdentity", "applicationState", "ownedWindowIdentity", "ownedWindowIsKey", "ownedWindowSceneIdentity", "ownedSceneActivationState"]
    static let maximumEncodedBytes = 16_384
    static let counterLimit = 2_147_483_647
    private(set) var registration: PassiveLifecycleRegistration = .notRegistered
    private(set) var tokenCount = 0
    private(set) var attempted = 0
    private(set) var dropped = 0
    private(set) var filtered = 0
    private(set) var issues: Set<PassiveLifecycleIssue> = []
    private var entries: [[String: Any]] = []
    private var lastFinished: Double?
    private let rowLimit: Int
    private let countLimit: Int
    // Finite host seams can only reduce production bounds, never raise them.
    init(rowLimit: Int = 64, countLimit: Int = 2_147_483_647) {
        precondition((1...Self.maximumRows).contains(rowLimit) && (1...Self.counterLimit).contains(countLimit))
        self.rowLimit = rowLimit; self.countLimit = countLimit
    }

    func register(tokens: Int) {
        guard registration == .notRegistered, tokens == PassiveLifecycleKind.allCases.count else {
            registration = .invalid; issues.insert(.registration); return
        }
        tokenCount = tokens; registration = .registered
    }
    func stop() { registration = .stopped; tokenCount = 0 }
    func ownershipEnded() {
        // UIKit may load the root view before launch registration. Preserve the
        // registration opportunity while truthfully recording that early gap.
        if registration == .notRegistered { increment(&attempted); reject(.registration); return }
        issues.insert(.ownership); stop()
    }
    func filteredNotification() { increment(&filtered) }
    func invalidSite() { increment(&attempted); reject(.data) }
    private func increment(_ value: inout Int) {
        if value < countLimit { value += 1 } else { issues.insert(.counter) }
    }
    private func reject(_ issue: PassiveLifecycleIssue) { issues.insert(issue); increment(&dropped) }

    private func envelope(rows: [[String: Any]], reserve: Bool = false, offMain: Int = 0) -> [String: Any] {
        var activeIssues = issues
        if registration != .registered { activeIssues.insert(.registration) }
        if offMain > 0 { activeIssues.insert(.thread) }
        if offMain >= Self.counterLimit { activeIssues.insert(.counter) }
        let issueNames = PassiveLifecycleIssue.allCases.filter { reserve || activeIssues.contains($0) }.map(\.rawValue)
        return ["schema": "mixer.apple-toggle.passive-lifecycle.1", "authoritative": false, "atomic": false,
                "maximumRows": Self.maximumRows, "maximumEncodedBytes": Self.maximumEncodedBytes,
                "registrationStatus": reserve ? PassiveLifecycleRegistration.invalid.rawValue : registration.rawValue,
                "scopeStatus": "owned-app-window-current-scene-only", "observerTokens": reserve ? 14 : tokenCount,
                "captureStatus": issueNames.isEmpty ? "complete" : "incomplete", "issues": issueNames,
                "truncated": reserve || issues.contains(.count) || issues.contains(.bytes),
                "attempted": reserve ? Self.counterLimit : attempted, "retained": rows.count,
                "dropped": reserve ? Self.counterLimit : dropped, "filtered": reserve ? Self.counterLimit : filtered,
                "offMainDeliveries": reserve ? Self.counterLimit : min(Self.counterLimit, max(0, offMain)), "rowSchema": "mixer.apple-toggle.passive-lifecycle-row.1", "columns": Self.columns,
                "identityEncoding": "object-address-lowercase-hex", "entries": rows.map { row in Self.columns.map { row[$0] ?? NSNull() } }]
    }
    static func encode(_ value: Any) -> Data? {
        try? JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
    }
    // Includes the envelope, largest counters/statuses and a full nested field
    // wrapper at the same depth/options used by the unchanged original persist.
    static func encodedField(_ value: [String: Any]) -> Data? {
        encode(["passiveLifecycleDiagnostic": value])
    }
    func value(offMain: Int = 0) -> [String: Any] { envelope(rows: entries, offMain: offMain) }
    func append(_ snapshot: PassiveLifecycleSnapshot) {
        guard attempted < countLimit else { reject(.counter); return }
        increment(&attempted)
        guard registration == .registered else { reject(.registration); return }
        guard snapshot.systemUptime.isFinite, snapshot.finishedUptime.isFinite,
              snapshot.systemUptime >= 0, snapshot.finishedUptime >= snapshot.systemUptime,
              lastFinished.map({ snapshot.systemUptime >= $0 }) ?? true else { reject(.timing); return }
        let callback = snapshot.site == .controllerCallback || snapshot.site == .carrierCallback
        let notification = snapshot.site == .notification
        guard snapshot.processIdentifier > 0, snapshot.processIdentifier <= Int(Int32.max),
              callback ? (snapshot.contextSequence.map { $0 > 0 && $0 <= Self.counterLimit } == true) : snapshot.contextSequence == nil,
              notification == (snapshot.notificationKind != nil), notification == (snapshot.notificationObjectIdentity != nil),
              snapshot.ownedWindowIdentity != nil, snapshot.ownedWindowIsKey != nil,
              (snapshot.ownedWindowSceneIdentity == nil) == (snapshot.ownedSceneActivationState == .absent) else { reject(.data); return }
        if snapshot.applicationState == .unknown || snapshot.ownedSceneActivationState == .unknown { issues.insert(.data) }
        guard entries.count < rowLimit else { reject(.count); return }
        let row: [String: Any] = ["sequence": attempted, "systemUptime": snapshot.systemUptime, "finishedUptime": snapshot.finishedUptime,
            "processIdentifier": snapshot.processIdentifier, "site": snapshot.site.rawValue,
            "contextSequence": snapshot.contextSequence as Any? ?? NSNull(),
            "notificationKind": snapshot.notificationKind?.rawValue as Any? ?? NSNull(),
            "notificationObjectIdentity": snapshot.notificationObjectIdentity?.value as Any? ?? NSNull(),
            "applicationState": snapshot.applicationState.rawValue, "ownedWindowIdentity": snapshot.ownedWindowIdentity?.value as Any? ?? NSNull(),
            "ownedWindowIsKey": snapshot.ownedWindowIsKey as Any? ?? NSNull(),
            "ownedWindowSceneIdentity": snapshot.ownedWindowSceneIdentity?.value as Any? ?? NSNull(),
            "ownedSceneActivationState": snapshot.ownedSceneActivationState.rawValue]
        let next = entries + [row]
        guard let reserved = Self.encodedField(envelope(rows: next, reserve: true)), reserved.count <= Self.maximumEncodedBytes else { reject(.bytes); return }
        entries = next; lastFinished = snapshot.finishedUptime
    }
}
