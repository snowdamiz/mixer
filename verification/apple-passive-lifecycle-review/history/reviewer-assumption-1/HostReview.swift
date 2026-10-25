import Foundation

// Independent finite controls over the exact candidate Foundation member.
// This file never substitutes for compiling or executing the UIKit adapter.
@main @MainActor struct HostReview {
    static var checks = 0
    static var largestField = 0
    static var smallestRetained = 64
    static var largestRetained = 0
    static let application = NSObject(), window = NSObject(), scene = NSObject(), otherScene = NSObject()

    static func check(_ label: String, _ value: @autoclosure () -> Bool) {
        guard value() else { fatalError("FAIL: \(label)") }
        checks += 1
        print("PASS: \(label)")
    }

    static func sample(_ n: Int, kind: PassiveLifecycleKind? = nil, mode: Int = 0) -> PassiveLifecycleSnapshot {
        let times: [Double] = [Double(n), Double(n) * 1.2345678901234567e-100,
            Double(n) / 100 * Double.greatestFiniteMagnitude, Double(n) * Double.leastNonzeroMagnitude]
        let hasScene = mode != 4
        let object = kind.map { $0.family == 0 ? application : $0.family == 1 ? window : scene }
        return PassiveLifecycleSnapshot(systemUptime: times[mode % 4], finishedUptime: times[mode % 4],
            processIdentifier: Int(Int32.max), site: kind == nil ? .carrierCallback : .notification,
            contextSequence: kind == nil ? PassiveLifecycleBuffer.counterLimit : nil,
            notificationKind: kind, notificationObjectIdentity: object.map(PassiveLifecycleIdentity.init),
            applicationState: mode == 5 ? .unknown : .background, ownedWindowIdentity: PassiveLifecycleIdentity(window),
            ownedWindowIsKey: mode % 2 == 0, ownedWindowSceneIdentity: hasScene ? PassiveLifecycleIdentity(scene) : nil,
            ownedSceneActivationState: hasScene ? (mode == 5 ? .unknown : .foregroundInactive) : .absent)
    }

    static func count(_ value: [String: Any]) -> Int { (value["entries"] as! [[Any]]).count }

    static func encoded(_ value: [String: Any]) -> Int {
        guard let data = PassiveLifecycleBuffer.encodedField(value) else { fatalError("field serialization refused") }
        largestField = max(largestField, data.count)
        return data.count
    }

    static func growthBound(_ buffer: PassiveLifecycleBuffer) -> Bool {
        let baseline = buffer.value()
        for registration in PassiveLifecycleRegistration.allCases {
            // All issues with truncation is a conservative superset of actual
            // post-retention metadata. Rows are actual immutable retained rows.
            var largest = baseline
            largest["registrationStatus"] = registration.rawValue
            largest["observerTokens"] = 14
            largest["issues"] = PassiveLifecycleIssue.allCases.map(\.rawValue)
            largest["captureStatus"] = "incomplete"
            largest["truncated"] = true
            for key in ["attempted", "dropped", "filtered", "offMainDeliveries"] { largest[key] = PassiveLifecycleBuffer.counterLimit }
            guard encoded(largest) <= 16_384 else { return false }
            // A reachable nontruncated value cannot include count/byte issues.
            largest["issues"] = PassiveLifecycleIssue.allCases.filter { $0 != .count && $0 != .bytes }.map(\.rawValue)
            largest["truncated"] = false
            guard encoded(largest) <= 16_384 else { return false }
        }
        return true
    }

    static func main() throws {
        let originalData = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
        let original = try JSONSerialization.jsonObject(with: originalData) as! [String: Any]
        let canonicalOriginal = PassiveLifecycleBuffer.encode(original)!
        check("Foundation options reproduce exact historical original packet bytes", originalData == canonicalOriginal)

        for kind in PassiveLifecycleKind.allCases {
            for mode in 0..<6 {
                let buffer = PassiveLifecycleBuffer()
                buffer.register(tokens: 14)
                for n in 1...96 { buffer.append(sample(n, kind: kind, mode: mode)) }
                let value = buffer.value(offMain: Int.max)
                let retained = count(value)
                smallestRetained = min(smallestRetained, retained)
                largestRetained = max(largestRetained, retained)
                check("real row and byte bounds \(kind.rawValue) mode \(mode)", retained > 0 && retained <= 64 && encoded(value) <= 16_384 && value["truncated"] as? Bool == true)
                check("every registration and maximum later metadata bounded \(kind.rawValue) mode \(mode)", growthBound(buffer))
                let before = PassiveLifecycleBuffer.encode(value["entries"]!)!
                buffer.append(sample(97, kind: kind, mode: 5))
                buffer.append(PassiveLifecycleSnapshot(systemUptime: .nan, finishedUptime: .nan, processIdentifier: 1,
                    site: .snapshot, contextSequence: nil, notificationKind: nil, notificationObjectIdentity: nil,
                    applicationState: .active, ownedWindowIdentity: PassiveLifecycleIdentity(window), ownedWindowIsKey: false,
                    ownedWindowSceneIdentity: nil, ownedSceneActivationState: .absent))
                buffer.invalidSite(); buffer.register(tokens: 0); buffer.ownershipEnded()
                for _ in 0..<32 { buffer.filteredNotification(); buffer.append(sample(98)) }
                let after = buffer.value(offMain: Int.max)
                check("actual post-refusal lifecycle metadata bounded without retained row mutation \(kind.rawValue) mode \(mode)", before == PassiveLifecycleBuffer.encode(after["entries"]!)! && encoded(after) <= 16_384 && after["observerTokens"] as? Int == 0 && after["captureStatus"] as? String == "incomplete")
                var supplemented = original
                supplemented["passiveLifecycleDiagnostic"] = after
                let addedBytes = PassiveLifecycleBuffer.encode(supplemented)!.count - canonicalOriginal.count
                supplemented.removeValue(forKey: "passiveLifecycleDiagnostic")
                check("actual root packet nesting fits standalone field reservation and preserves original \(kind.rawValue) mode \(mode)", addedBytes <= encoded(after) && PassiveLifecycleBuffer.encode(supplemented) == canonicalOriginal)
            }
        }

        let callbacks = PassiveLifecycleBuffer(); callbacks.register(tokens: 14)
        for n in 1...96 { callbacks.append(sample(n)) }
        check("maximum valid callback context and pid bounded", count(callbacks.value()) > 0 && growthBound(callbacks))
        check("callback context maximum preserved", ((callbacks.value()["entries"] as! [[Any]])[0][5] as? Int) == PassiveLifecycleBuffer.counterLimit)
        let short = PassiveLifecycleBuffer(); short.register(tokens: 14)
        for n in 1...96 { short.append(sample(n, mode: 4)) }
        check("absent scene callback workload remains bounded", count(short.value()) <= 64 && growthBound(short))

        for gaps in [0, 1, 3, 7] {
            let buffer = PassiveLifecycleBuffer()
            for _ in 0..<gaps { buffer.ownershipEnded(); buffer.append(sample(1)) }
            buffer.register(tokens: 14)
            buffer.append(sample(1))
            let value = buffer.value()
            check("early gaps preserve later real registration \(gaps)", buffer.registration == .registered && buffer.tokenCount == 14 && count(value) == 1 && buffer.attempted == gaps * 2 + 1 && buffer.dropped == gaps * 2)
            let first = (value["entries"] as! [[Any]])[0]
            check("early gap remains explicit in first retained sequence \(gaps)", first[0] as? Int == gaps * 2 + 1 && (gaps == 0 || buffer.issues.contains(.registration)))
        }

        var app: NSObject? = NSObject(), ownedWindow: NSObject? = NSObject()
        let scope = PassiveLifecycleOwnership(application: app!, window: ownedWindow!)
        let currentApp = app!
        check("current scene replacement excludes previous scene", scope.accepts(.sceneActive, object: otherScene, currentScene: otherScene) && !scope.accepts(.sceneDisconnect, object: scene, currentScene: otherScene))
        weak var windowProbe = ownedWindow
        ownedWindow = nil
        check("window ownership remains weak", windowProbe == nil && scope.window == nil)
        check("missing owned window rejects every event family", !scope.accepts(.appActive, object: currentApp, currentScene: scene) && !scope.accepts(.windowKey, object: window, currentScene: scene) && !scope.accepts(.sceneActive, object: scene, currentScene: scene))
        app = nil

        let center = NotificationCenter(), faults = PassiveLifecycleDeliveryFaults()
        var tokens: PassiveLifecycleTokens? = PassiveLifecycleTokens(center: center)
        weak var bagProbe = tokens
        for _ in 0..<14 {
            let token = center.addObserver(forName: .init("review-token"), object: nil, queue: nil) { _ in faults.record() }
            check("finite actual token inserted", tokens!.insert(token))
        }
        let overflow = center.addObserver(forName: .init("review-token"), object: nil, queue: nil) { _ in faults.record() }
        check("overflow token immediately unregistered", !tokens!.insert(overflow) && tokens!.count == 14)
        center.post(name: .init("review-token"), object: nil)
        check("only bounded token set delivers", faults.value == 14)
        tokens = nil
        center.post(name: .init("review-token"), object: nil)
        check("bag deinit releases actual registrations", bagProbe == nil && faults.value == 14)
        DispatchQueue.concurrentPerform(iterations: 512) { _ in faults.record() }
        check("concurrent delivery accounting preserves all finite calls", faults.value == 526)

        let seam = PassiveLifecycleBuffer(rowLimit: 1, countLimit: 3); seam.register(tokens: 14)
        for n in 1...16 { seam.append(sample(n)); seam.filteredNotification() }
        check("saturation seam bounds every mutable local counter", seam.attempted == 3 && seam.dropped == 3 && seam.filtered == 3 && seam.issues.contains(.counter) && growthBound(seam))
        check("negative external fault input cannot create negative export", seam.value(offMain: -1)["offMainDeliveries"] as? Int == 0)
        print("{\"passed\":true,\"checks\":\(checks),\"notificationWorkloads\":84,\"largestEncodedFieldBytes\":\(largestField),\"minimumRetainedNotificationRows\":\(smallestRetained),\"maximumRetainedNotificationRows\":\(largestRetained),\"uikitCompiled\":false,\"nativeExecution\":false}")
    }
}
