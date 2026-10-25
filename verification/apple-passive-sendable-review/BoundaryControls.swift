import UIKit

// Independent finite boundary checks. The observer/data bytes are extracted
// from the selected archives; UIKit is a labeled macOS public-surface double.
@main @MainActor struct BoundaryControls {
    static var checks = 0
    static func check(_ label: String, _ condition: @autoclosure () -> Bool) {
        precondition(condition(), label); checks += 1; print("PASS: \(label)")
    }
    static func rows(_ observer: PassiveLifecycleObserver) -> [[Any]] { observer.value["entries"] as! [[Any]] }
    static func counter(_ observer: PassiveLifecycleObserver, _ name: String) -> Int { observer.value[name] as! Int }
    static func identity(_ object: AnyObject) -> String {
        "0x" + String(UInt(bitPattern: Unmanaged.passUnretained(object).toOpaque()), radix: 16)
    }
    static func fixture() -> (PassiveLifecycleObserver, UIWindow, UIScene) {
        let observer = PassiveLifecycleObserver(), window = UIWindow(), scene = UIScene()
        window.windowScene = scene; observer.start(application: .shared, window: window)
        return (observer, window, scene)
    }
    static func main() throws {
        check("host is main thread", Thread.isMainThread)
        let families: [(Notification.Name, String)] = [
            (.init("UIApplicationDidBecomeActiveNotification"), "app"),
            (.init("UIWindowDidBecomeKeyNotification"), "window"),
            (.init("UISceneDidActivateNotification"), "scene")
        ]
        for (name, family) in families {
            let (observer, window, scene) = fixture()
            let owned: AnyObject = ["app": UIApplication.shared, "window": window, "scene": scene][family]!
            let foreigns: [Any?] = [nil, "bridged-string", 17, NSNull(), NSObject()]
            for object in foreigns { NotificationCenter.default.post(name: name, object: object) }
            check("\(family) nil and bridged foreign identity refused", rows(observer).count == 1 && counter(observer, "filtered") == 5 && counter(observer, "attempted") == 1)
            NotificationCenter.default.post(name: name, object: owned)
            check("\(family) exact live object synchronously accepted", rows(observer).count == 2 && rows(observer).last![7] as? String == identity(owned))
        }
        do {
            let (observer, window, old) = fixture(), replacement = UIScene()
            window.onSceneRead = {
                window.onSceneRead = nil
                window.windowScene = replacement
                NotificationCenter.default.post(name: .init("UISceneDidActivateNotification"), object: replacement)
            }
            NotificationCenter.default.post(name: .init("UISceneDidActivateNotification"), object: old)
            check("nested synchronous delivery filters stale outer scene", rows(observer).count == 2 && counter(observer, "filtered") == 1)
            check("nested scene row is actual current object", rows(observer).last![7] as? String == identity(replacement) && rows(observer).last![11] as? String == identity(replacement))
            NotificationCenter.default.post(name: .init("UISceneDidActivateNotification"), object: replacement)
            check("later current scene remains observable", rows(observer).count == 3 && counter(observer, "attempted") == 3)
        }
        do {
            let (observer, window, _) = fixture(), done = DispatchSemaphore(value: 0)
            let encodedBefore = PassiveLifecycleBuffer.encode(rows(observer))!
            let readsBefore = window.sceneReadCount
            DispatchQueue.global().async {
                // Non-nil objects are created and destroyed in this closure;
                // no actor object is sent by the test to another executor.
                for name in ["UIApplicationDidBecomeActiveNotification", "UIWindowDidBecomeKeyNotification", "UISceneDidActivateNotification"] {
                    NotificationCenter.default.post(name: .init(name), object: NSObject())
                }
                done.signal()
            }
            check("off-main nonnil delivery is synchronous and completes", done.wait(timeout: .now() + 5) == .success)
            check("off-main nonnil delivery records only faults", counter(observer, "offMainDeliveries") == 3 && counter(observer, "filtered") == 0 && counter(observer, "attempted") == 1)
            check("off-main delivery reads no actor state", window.sceneReadCount == readsBefore && PassiveLifecycleBuffer.encode(rows(observer))! == encodedBefore)
        }
        do {
            let observer = PassiveLifecycleObserver(), scene = UIScene()
            var owned: UIWindow? = UIWindow()
            weak var probe = owned
            owned!.windowScene = scene; observer.start(application: .shared, window: owned!)
            let releasedIdentity = identity(owned!)
            owned = nil
            check("identity projection creates no lasting window ownership", probe == nil)
            // A new object cannot qualify stale ownership, regardless of its
            // eventual address. Ended weak ownership is checked first.
            let replacement = UIWindow()
            NotificationCenter.default.post(name: .init("UIWindowDidBecomeKeyNotification"), object: replacement)
            check("ended owner refuses any replacement address", rows(observer).count == 1 && observer.value["registrationStatus"] as? String == "stopped" && counter(observer, "observerTokens") == 0)
            check("ended owner leaves captured identity unchanged", rows(observer)[0][9] as? String == releasedIdentity)
        }
        do {
            let (observer, window, _) = fixture()
            var old: UIScene? = UIScene()
            weak var weakOld = old
            window.windowScene = old
            let oldIdentity = identity(old!)
            let replacement = UIScene()
            var aliveInside = false
            window.sceneReadCount = 0
            window.onSceneRead = {
                if window.sceneReadCount == 2 {
                    window.onSceneRead = nil
                    window.windowScene = replacement; old = nil
                    aliveInside = weakOld != nil
                }
            }
            NotificationCenter.default.post(name: .init("UISceneDidActivateNotification"), object: old)
            check("actual projected object stays live inside synchronous capture", aliveInside && rows(observer).last![7] as? String == oldIdentity)
            check("sequential snapshot sees replacement association", rows(observer).last![11] as? String == identity(replacement))
            check("actual projected object releases after callback", weakOld == nil)
        }
        print(String(data: try JSONSerialization.data(withJSONObject: ["passed": true, "checks": checks, "scope": "independent-macOS-NotificationCenter-boundary-UIKit-double", "realUIKitExecuted": false, "nativeExecution": false], options: [.sortedKeys]), encoding: .utf8)!)
    }
}
