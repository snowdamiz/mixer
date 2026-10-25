import Foundation

@main @MainActor struct HostTests {
    static var checks = 0
    static func check(_ name: String, _ condition: @autoclosure () -> Bool) {
        guard condition() else { fatalError("FAIL: \(name)") }
        checks += 1; print("PASS: \(name)")
    }
    static let app = NSObject(), window = NSObject(), scene = NSObject(), other = NSObject()
    static func snapshot(time: Double = 1, end: Double? = nil, pid: Int = 100,
                         site: PassiveLifecycleSite = .snapshot, context: Int? = nil,
                         kind: PassiveLifecycleKind? = nil, object: AnyObject? = nil,
                         appState: PassiveLifecycleAppState = .active, hasWindow: Bool = true, key: Bool? = true,
                         hasScene: Bool = true, sceneState: PassiveLifecycleSceneState = .foregroundActive) -> PassiveLifecycleSnapshot {
        PassiveLifecycleSnapshot(systemUptime: time, finishedUptime: end ?? time, processIdentifier: pid, site: site,
            contextSequence: context, notificationKind: kind, notificationObjectIdentity: object.map(PassiveLifecycleIdentity.init),
            applicationState: appState, ownedWindowIdentity: hasWindow ? PassiveLifecycleIdentity(window) : nil, ownedWindowIsKey: key,
            ownedWindowSceneIdentity: hasScene ? PassiveLifecycleIdentity(scene) : nil, ownedSceneActivationState: sceneState)
    }
    static func ready(rows: Int = 64, counter: Int = PassiveLifecycleBuffer.counterLimit) -> PassiveLifecycleBuffer {
        let b = PassiveLifecycleBuffer(rowLimit: rows, countLimit: counter); b.register(tokens: 14); return b
    }
    static func rows(_ b: PassiveLifecycleBuffer) -> [[String: Any]] { (b.value()["entries"] as! [[Any]]).map { row in Dictionary(uniqueKeysWithValues: zip(PassiveLifecycleBuffer.columns, row)) } }
    static func cap(_ b: PassiveLifecycleBuffer, offMain: Int = 0) -> Bool {
        guard let bytes = PassiveLifecycleBuffer.encodedField(b.value(offMain: offMain)) else { return false }
        return bytes.count <= PassiveLifecycleBuffer.maximumEncodedBytes && rows(b).count <= 64
    }
    static func main() throws {
        let empty = PassiveLifecycleBuffer()
        check("initial status not registered", empty.value()["registrationStatus"] as? String == "not-registered")
        check("empty envelope fits cap", cap(empty))
        empty.append(snapshot())
        check("pre-registration snapshot is dropped truthfully", empty.dropped == 1 && empty.issues.contains(.registration) && rows(empty).isEmpty)
        for n in [0, 13, 15, Int.max] {
            let b = PassiveLifecycleBuffer(); b.register(tokens: n)
            check("invalid registration \(n) fails closed", b.registration == .invalid && b.issues.contains(.registration) && cap(b))
        }
        let registered = ready()
        registered.append(snapshot(site: .registration, hasScene: false, sceneState: .absent))
        check("registered token count exact", registered.tokenCount == 14 && registered.registration == .registered)
        check("initial absent scene explicit", rows(registered).first?["ownedSceneActivationState"] as? String == "absent" && rows(registered).first?["ownedWindowSceneIdentity"] is NSNull)
        check("supplement explicitly non authoritative and non atomic", registered.value()["authoritative"] as? Bool == false && registered.value()["atomic"] as? Bool == false)
        registered.append(snapshot(time: 2))
        check("later actual association is retained", rows(registered).last?["ownedSceneActivationState"] as? String == "foreground-active")
        registered.append(snapshot(time: 3, site: .controllerCallback, context: 1))
        registered.append(snapshot(time: 4, site: .carrierCallback, context: 2))
        check("existing callback metadata retained", rows(registered).suffix(2).map { $0["contextSequence"] as! Int } == [1,2])
        registered.register(tokens: 14)
        check("duplicate registration explicit incomplete", registered.registration == .invalid && registered.issues.contains(.registration))
        let stopped = ready(); stopped.ownershipEnded(); stopped.append(snapshot())
        check("ownership end marks stopped removes advertised tokens", stopped.registration == .stopped && stopped.tokenCount == 0 && stopped.issues.contains(.ownership) && stopped.dropped == 1)

        let byCount = ready(rows: 2)
        for n in 0..<8 { byCount.append(snapshot(time: Double(n))) }
        check("reduced-only row seam exercises actual row overflow", rows(byCount).count == 2 && byCount.dropped == 6 && byCount.attempted == 8 && byCount.issues.contains(.count))
        let byBytes = ready()
        for n in 0..<100 { byBytes.append(snapshot(time: Double(n), site: .notification, kind: .sceneInactive, object: scene)) }
        let retained = rows(byBytes).count
        check("production byte overflow exercised before 64 rows", retained > 0 && retained < 64 && byBytes.issues.contains(.bytes))
        let beforeRows = PassiveLifecycleBuffer.encode(rows(byBytes))!
        for _ in 0..<2_000 { byBytes.append(snapshot(time: 101, site: .notification, kind: .sceneInactive, object: scene)); byBytes.filteredNotification() }
        byBytes.invalidSite(); byBytes.register(tokens: 0); byBytes.ownershipEnded()
        check("post-refusal counters grow while rows byte exact", beforeRows == PassiveLifecycleBuffer.encode(rows(byBytes))! && byBytes.filtered == 2_000 && byBytes.dropped > 2_000)
        check("all later statuses maximum off-main counter still capped", cap(byBytes, offMain: Int.max))
        let encodedEnvelope = byBytes.value(offMain: Int.max)
        let encodedRows = encodedEnvelope["entries"] as! [[Any]]
        check("closed versioned columns exactly thirteen", encodedEnvelope["columns"] as! [String] == ["sequence", "systemUptime", "finishedUptime", "processIdentifier", "site", "contextSequence", "notificationKind", "notificationObjectIdentity", "applicationState", "ownedWindowIdentity", "ownedWindowIsKey", "ownedWindowSceneIdentity", "ownedSceneActivationState"] && encodedEnvelope["rowSchema"] as? String == "mixer.apple-toggle.passive-lifecycle-row.1")
        check("every retained row exact column arity", encodedRows.allSatisfy { $0.count == 13 })
        check("fixed integer time enum identity bool types", encodedRows.allSatisfy { row in row[0] is Int && row[1] is Double && row[2] is Double && row[3] is Int && row[4] as? String == "notification" && row[5] is NSNull && row[6] as? String == "scene-will-deactivate" && row[7] is String && row[8] as? String == "active" && row[9] is String && row[10] is Bool && row[11] is String && row[12] as? String == "foreground-active" })
        check("identities use actual object address", PassiveLifecycleIdentity(window).value == "0x" + String(UInt(bitPattern: Unmanaged.passUnretained(window).toOpaque()), radix: 16))
        check("truncation explicit after byte refusal", encodedEnvelope["truncated"] as? Bool == true)
        let bytes = PassiveLifecycleBuffer.encodedField(encodedEnvelope)!
        check("pretty sorted whole supplementary field encodes under 16384", bytes.count <= 16_384)
        let counter = ready(rows: 1, counter: 3)
        for n in 0..<20 { counter.append(snapshot(time: Double(n))); counter.filteredNotification() }
        check("attempted dropped filtered counters saturate", counter.attempted == 3 && counter.dropped == 3 && counter.filtered == 3 && counter.issues.contains(.counter))
        check("counter overflow does not escape cap", cap(counter))

        for (name, row) in [
            ("nan-start", snapshot(time: .nan)), ("infinite-start", snapshot(time: .infinity)),
            ("negative-start", snapshot(time: -1)), ("nan-finish", snapshot(end: .nan)),
            ("infinite-finish", snapshot(end: .infinity)), ("reversed-time", snapshot(time: 2, end: 1))
        ] { let b = ready(); b.append(row); check("invalid timing \(name)", rows(b).isEmpty && b.issues.contains(.timing) && cap(b)) }
        let monotonic = ready(); monotonic.append(snapshot(time: 1, end: 2)); monotonic.append(snapshot(time: 1.9)); monotonic.append(snapshot(time: 2))
        check("sequential time rejects overlap allows equal endpoint", rows(monotonic).count == 2 && monotonic.dropped == 1 && monotonic.issues.contains(.timing))
        for (name, row) in [
            ("pid-zero", snapshot(pid: 0)), ("pid-too-large", snapshot(pid: Int.max)),
            ("snapshot-context", snapshot(context: 1)), ("callback-missing-context", snapshot(site: .controllerCallback)),
            ("callback-zero-context", snapshot(site: .carrierCallback, context: 0)),
            ("callback-huge-context", snapshot(site: .controllerCallback, context: Int.max)),
            ("notification-no-kind", snapshot(site: .notification, object: app)),
            ("notification-no-object", snapshot(site: .notification, kind: .appActive)),
            ("snapshot-with-kind", snapshot(kind: .appActive)), ("snapshot-with-object", snapshot(object: app)),
            ("window-missing", snapshot(hasWindow: false)), ("key-missing", snapshot(key: nil)),
            ("scene-missing-with-state", snapshot(hasScene: false)), ("scene-present-absent-state", snapshot(sceneState: .absent))
        ] { let b = ready(); b.append(row); check("closed metadata rejects \(name)", rows(b).isEmpty && b.issues.contains(.data) && cap(b)) }
        for state in PassiveLifecycleAppState.allCases {
            let b = ready(); b.append(snapshot(appState: state)); check("app state \(state.rawValue) explicit", rows(b).count == 1 && rows(b)[0]["applicationState"] as? String == state.rawValue)
            if state == .unknown { check("unknown app state incomplete", b.issues.contains(.data)) }
        }
        for state in PassiveLifecycleSceneState.allCases {
            let b = ready(); b.append(snapshot(hasScene: state != .absent, sceneState: state))
            check("scene state \(state.rawValue) explicit", rows(b).count == 1 && rows(b)[0]["ownedSceneActivationState"] as? String == state.rawValue)
            if state == .unknown { check("unknown scene state incomplete", b.issues.contains(.data)) }
        }
        let scope = PassiveLifecycleOwnership(application: app, window: window)
        for kind in PassiveLifecycleKind.allCases {
            let actual = kind.family == 0 ? app : kind.family == 1 ? window : scene
            check("owned identity filter \(kind.rawValue)", scope.accepts(kind, object: actual, currentScene: scene) && !scope.accepts(kind, object: other, currentScene: scene) && !scope.accepts(kind, object: nil, currentScene: scene))
            let b = ready(); b.append(snapshot(site: .notification, kind: kind, object: actual))
            check("closed notification kind serializes \(kind.rawValue)", rows(b).count == 1 && rows(b)[0]["notificationKind"] as? String == kind.rawValue)
        }
        check("no association cannot adopt another scene", !scope.accepts(.sceneConnect, object: scene, currentScene: nil))
        check("changed association excludes old scene", !scope.accepts(.sceneDisconnect, object: scene, currentScene: other) && scope.accepts(.sceneActive, object: other, currentScene: other))
        var temporaryApp: NSObject? = NSObject(), temporaryWindow: NSObject? = NSObject()
        let weakScope = PassiveLifecycleOwnership(application: temporaryApp!, window: temporaryWindow!)
        weak var appProbe = temporaryApp, windowProbe = temporaryWindow
        temporaryApp = nil; temporaryWindow = nil
        check("scope does not retain application or window", appProbe == nil && windowProbe == nil && weakScope.application == nil && weakScope.window == nil)
        check("ended ownership cannot accept events", !weakScope.accepts(.appActive, object: app, currentScene: scene))

        let center = NotificationCenter(); let fault = PassiveLifecycleDeliveryFaults()
        var bag: PassiveLifecycleTokens? = PassiveLifecycleTokens(center: center)
        for _ in 0..<14 { check("bounded token admitted", bag!.insert(center.addObserver(forName: Notification.Name("owned-test"), object: nil, queue: nil) { _ in fault.record() })) }
        let overflowToken = center.addObserver(forName: Notification.Name("owned-test"), object: nil, queue: nil) { _ in fault.record() }
        check("fifteenth token removed immediately", !bag!.insert(overflowToken) && bag!.count == 14)
        center.post(name: Notification.Name("owned-test"), object: nil)
        check("exactly fourteen registrations delivered", fault.value == 14)
        bag!.removeAll(); center.post(name: Notification.Name("owned-test"), object: nil)
        check("explicit token removal ends delivery", fault.value == 14 && bag!.count == 0)
        _ = bag!.insert(center.addObserver(forName: Notification.Name("owned-test"), object: nil, queue: nil) { _ in fault.record() })
        bag = nil; center.post(name: Notification.Name("owned-test"), object: nil)
        check("token bag deinit unregisters", fault.value == 14)
        check("off-main fault reported without rows", (empty.value(offMain: 1)["issues"] as! [String]).contains("incomplete-thread") && empty.value(offMain: 1)["offMainDeliveries"] as? Int == 1)
        check("off-main count clamped and saturation truthful", empty.value(offMain: Int.max)["offMainDeliveries"] as? Int == PassiveLifecycleBuffer.counterLimit && (empty.value(offMain: Int.max)["issues"] as! [String]).contains("incomplete-counter"))
        DispatchQueue.concurrentPerform(iterations: 400) { _ in fault.record() }
        check("shared delivery fault counter thread safe", fault.value == 414)

        let originalData = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let original = try JSONSerialization.jsonObject(with: originalData) as! [String: Any]
        var supplemented = original
        supplemented["passiveLifecycleDiagnostic"] = byBytes.value(offMain: Int.max)
        supplemented.removeValue(forKey: "passiveLifecycleDiagnostic")
        check("actual original packet data retention after supplementary merge", NSDictionary(dictionary: original).isEqual(to: supplemented))
        check("actual original serialized payload retained byte exact", PassiveLifecycleBuffer.encode(original) == PassiveLifecycleBuffer.encode(supplemented))
        print("{\"passed\":true,\"checks\":\(checks),\"productionRetainedRowsAtByteLimit\":\(retained),\"maximumTestFieldBytes\":\(bytes.count),\"nativeExecution\":false,\"uikitCompiled\":false}")
    }
}
