import UIKit

// Calls the exact archived adapter through real synchronous NotificationCenter
// delivery. Expected names/kinds/objects are an explicit contract table rather
// than a second implementation of the production family-selection algorithm.
@main @MainActor struct SemanticTests {
    static var checks = 0
    static var transcript: [[String: Any]] = []
    static let cases: [(Notification.Name, String, String)] = [
        (.init("UIApplicationDidBecomeActiveNotification"), "app-did-become-active", "app"),
        (.init("UIApplicationWillResignActiveNotification"), "app-will-resign-active", "app"),
        (.init("UIApplicationWillEnterForegroundNotification"), "app-will-enter-foreground", "app"),
        (.init("UIApplicationDidEnterBackgroundNotification"), "app-did-enter-background", "app"),
        (.init("UIWindowDidBecomeKeyNotification"), "window-did-become-key", "window"),
        (.init("UIWindowDidResignKeyNotification"), "window-did-resign-key", "window"),
        (.init("UIWindowDidBecomeVisibleNotification"), "window-did-become-visible", "window"),
        (.init("UIWindowDidBecomeHiddenNotification"), "window-did-become-hidden", "window"),
        (.init("UISceneWillConnectNotification"), "scene-will-connect", "scene"),
        (.init("UISceneDidDisconnectNotification"), "scene-did-disconnect", "scene"),
        (.init("UISceneDidActivateNotification"), "scene-did-activate", "scene"),
        (.init("UISceneWillDeactivateNotification"), "scene-will-deactivate", "scene"),
        (.init("UISceneWillEnterForegroundNotification"), "scene-will-enter-foreground", "scene"),
        (.init("UISceneDidEnterBackgroundNotification"), "scene-did-enter-background", "scene")
    ]
    static func check(_ label: String, _ ok: @autoclosure () -> Bool) {
        precondition(ok(), "FAIL: \(label)"); checks += 1; print("PASS: \(label)")
    }
    static func rows(_ o: PassiveLifecycleObserver) -> [[Any]] { o.value["entries"] as! [[Any]] }
    static func count(_ o: PassiveLifecycleObserver, _ key: String) -> Int { o.value[key] as! Int }
    static func identity(_ object: AnyObject) -> String {
        "0x" + String(UInt(bitPattern: Unmanaged.passUnretained(object).toOpaque()), radix: 16)
    }
    static func post(_ name: Notification.Name, _ object: AnyObject?) {
        NotificationCenter.default.post(name: name, object: object)
    }
    static func fixture() -> (PassiveLifecycleObserver, UIWindow, UIScene) {
        let o = PassiveLifecycleObserver(), w = UIWindow(), s = UIScene()
        w.windowScene = s; o.start(application: .shared, window: w)
        return (o, w, s)
    }
    static func main() throws {
        check("finite control executes on main thread", Thread.isMainThread)
        check("contract has fourteen distinct notification names", cases.count == 14 && Set(cases.map { $0.0 }).count == 14)
        for (name, expectedKind, owner) in cases {
            let (o, w, s) = fixture()
            let actual: AnyObject = ["app": UIApplication.shared, "window": w, "scene": s][owner]!
            let wrong: AnyObject = owner == "app" ? w : UIApplication.shared
            let initial = rows(o)
            check("\(expectedKind) launch registration is synchronous", initial.count == 1 && initial[0][4] as? String == "registration" && count(o, "observerTokens") == 14)
            post(name, nil); post(name, NSObject()); post(name, wrong)
            check("\(expectedKind) nil foreign and wrong family refused", rows(o).count == 1 && count(o, "filtered") == 3 && count(o, "attempted") == 1)
            post(name, actual)
            let row = rows(o).last!
            check("\(expectedKind) exact object synchronously captured", rows(o).count == 2 && count(o, "attempted") == 2 && row[6] as? String == expectedKind && row[7] as? String == identity(actual))
            check("\(expectedKind) sequential owned context preserved", row[4] as? String == "notification" && row[5] is NSNull && row[8] as? String == "active" && row[9] as? String == identity(w) && row[10] as? Bool == true && row[11] as? String == identity(s) && row[12] as? String == "foreground-active")
            post(.init("NotARegisteredLifecycleNotification"), actual)
            check("\(expectedKind) unrelated notification ignored", count(o, "attempted") == 2 && count(o, "filtered") == 3)
            transcript.append(["kind": row[6], "owner": owner, "site": row[4], "rows": rows(o).count, "attempted": count(o, "attempted"), "filtered": count(o, "filtered"), "context": "owned-current-scene"])
        }

        do {
            let (o, w, oldScene) = fixture(), newScene = UIScene()
            w.windowScene = newScene
            post(.init("UISceneDidDisconnectNotification"), oldScene)
            post(.init("UISceneDidActivateNotification"), newScene)
            check("association replacement rejects old scene and accepts current", rows(o).count == 2 && count(o, "filtered") == 1 && rows(o).last![7] as? String == identity(newScene))
            w.windowScene = nil
            post(.init("UISceneDidActivateNotification"), newScene)
            post(.init("UIApplicationDidBecomeActiveNotification"), UIApplication.shared)
            post(.init("UIWindowDidBecomeKeyNotification"), w)
            check("absent association rejects scene but preserves app and window", rows(o).count == 4 && count(o, "filtered") == 2 && rows(o).last![11] is NSNull && rows(o).last![12] as? String == "absent")
        }
        do {
            let o = PassiveLifecycleObserver(), w = UIWindow(), replacement = UIScene()
            var original: UIScene? = UIScene()
            weak var probe = original
            let originalIdentity = identity(original!)
            w.windowScene = original
            o.start(application: .shared, window: w); w.sceneReadCount = 0
            var aliveDuringCapture = false
            w.onSceneRead = { [weak w] in
                if w?.sceneReadCount == 2 {
                    w?.windowScene = replacement; original = nil
                    aliveDuringCapture = probe != nil
                }
            }
            post(.init("UISceneDidActivateNotification"), original)
            let row = rows(o).last!
            check("actual notification object survives synchronous capture", aliveDuringCapture && row[7] as? String == originalIdentity)
            check("filter and snapshot keep sequential scene reads", w.sceneReadCount == 2 && row[11] as? String == identity(replacement))
            check("notification object released after synchronous return", probe == nil)
            w.onSceneRead = nil
        }
        do {
            let (o, w, _) = fixture()
            var foreign: NSObject? = NSObject()
            weak var probe = foreign
            var heldDuringFilter = false
            w.onSceneRead = { foreign = nil; heldDuringFilter = probe != nil }
            post(.init("UISceneDidActivateNotification"), foreign)
            check("foreign actual object survives filtering without retention", heldDuringFilter && probe == nil && rows(o).count == 1 && count(o, "filtered") == 1)
            w.onSceneRead = nil
        }
        do {
            let o = PassiveLifecycleObserver()
            var w: UIWindow? = UIWindow(); w!.windowScene = UIScene()
            weak var probe = w
            o.start(application: .shared, window: w!); w = nil
            check("observer does not retain owned window", probe == nil)
            post(.init("UIApplicationDidBecomeActiveNotification"), UIApplication.shared)
            check("ended ownership stops registration on delivery", o.value["registrationStatus"] as? String == "stopped" && count(o, "observerTokens") == 0 && rows(o).count == 1 && (o.value["issues"] as! [String]).contains("incomplete-ownership"))
            post(.init("UIApplicationDidBecomeActiveNotification"), UIApplication.shared)
            check("ended ownership removed actual subscriptions", count(o, "attempted") == 1)
        }
        do {
            let w = UIWindow()
            var o: PassiveLifecycleObserver? = PassiveLifecycleObserver()
            weak var probe = o
            o!.start(application: .shared, window: w); o = nil
            check("notification callbacks retain observer weakly", probe == nil)
            post(.init("UIWindowDidBecomeKeyNotification"), w)
            check("post after observer destruction returns synchronously", probe == nil)
        }
        do {
            var app: NSObject? = NSObject(), window: NSObject? = NSObject()
            weak var appProbe = app, windowProbe = window
            let ownership = PassiveLifecycleOwnership(application: app!, window: window!)
            app = nil; window = nil
            check("shared ownership helper retains neither application nor window", appProbe == nil && windowProbe == nil && ownership.application == nil && ownership.window == nil)
        }
        do {
            let (o, w, _) = fixture(), done = DispatchSemaphore(value: 0)
            let names = cases.map { $0.0 }
            let before = PassiveLifecycleBuffer.encode(rows(o))!
            DispatchQueue.global().async {
                for name in names { NotificationCenter.default.post(name: name, object: nil) }
                done.signal()
            }
            check("finite off-main delivery completes without main hop", done.wait(timeout: .now() + 5) == .success)
            check("all off-main names report faults without actor mutation", count(o, "offMainDeliveries") == 14 && count(o, "attempted") == 1 && count(o, "filtered") == 0 && PassiveLifecycleBuffer.encode(rows(o))! == before && w.sceneReadCount == 1 && (o.value["issues"] as! [String]).contains("incomplete-thread"))
        }
        do {
            let (o, w, s) = fixture()
            for _ in 0..<16 {
                for (name, _, owner) in cases {
                    let object: AnyObject = ["app": UIApplication.shared, "window": w, "scene": s][owner]!
                    post(name, object)
                }
            }
            let retained = PassiveLifecycleBuffer.encode(rows(o))!
            let field = PassiveLifecycleBuffer.encodedField(o.value)!
            check("actual observer workload respects original row and byte bounds", !rows(o).isEmpty && rows(o).count <= 64 && field.count <= 16_384 && count(o, "attempted") == 225 && count(o, "dropped") > 0 && o.value["truncated"] as? Bool == true)
            for _ in 0..<16 { post(.init("UISceneDidActivateNotification"), s) }
            o.sample(site: "invalid-site", contextSequence: nil)
            check("refused rows and metadata remain bounded without mutation", PassiveLifecycleBuffer.encode(rows(o))! == retained && PassiveLifecycleBuffer.encodedField(o.value)!.count <= 16_384)
        }
        let output: [String: Any] = ["passed": true, "checks": checks, "notificationKinds": 14, "transcript": transcript, "scope": "macOS-real-NotificationCenter-exact-adapter-UIKit-double", "realUIKitExecuted": false, "nativeExecution": false]
        print(String(data: try JSONSerialization.data(withJSONObject: output, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
