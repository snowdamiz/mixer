// Finite macOS test double only. This module is never an iOS build input.
// It supplies public property/notification surfaces; it contains no observer,
// filtering, projection, buffering, threading, or focus implementation.
@_exported import Foundation

@MainActor public final class UIApplication: NSObject {
    public enum State { case active, inactive, background }
    public static let shared = UIApplication()
    public var applicationState: State = .active
    public static let didBecomeActiveNotification = Notification.Name("UIApplicationDidBecomeActiveNotification")
    public static let willResignActiveNotification = Notification.Name("UIApplicationWillResignActiveNotification")
    public static let willEnterForegroundNotification = Notification.Name("UIApplicationWillEnterForegroundNotification")
    public static let didEnterBackgroundNotification = Notification.Name("UIApplicationDidEnterBackgroundNotification")
}

@MainActor public final class UIScene: NSObject {
    public enum ActivationState { case unattached, foregroundActive, foregroundInactive, background }
    public var activationState: ActivationState = .foregroundActive
    public static let willConnectNotification = Notification.Name("UISceneWillConnectNotification")
    public static let didDisconnectNotification = Notification.Name("UISceneDidDisconnectNotification")
    public static let didActivateNotification = Notification.Name("UISceneDidActivateNotification")
    public static let willDeactivateNotification = Notification.Name("UISceneWillDeactivateNotification")
    public static let willEnterForegroundNotification = Notification.Name("UISceneWillEnterForegroundNotification")
    public static let didEnterBackgroundNotification = Notification.Name("UISceneDidEnterBackgroundNotification")
}

@MainActor public final class UIWindow: NSObject {
    public var isKeyWindow = true
    private var storedScene: UIScene?
    public var sceneReadCount = 0
    public var onSceneRead: (() -> Void)?
    public var windowScene: UIScene? {
        get { sceneReadCount += 1; onSceneRead?(); return storedScene }
        set { storedScene = newValue }
    }
    public static let didBecomeKeyNotification = Notification.Name("UIWindowDidBecomeKeyNotification")
    public static let didResignKeyNotification = Notification.Name("UIWindowDidResignKeyNotification")
    public static let didBecomeVisibleNotification = Notification.Name("UIWindowDidBecomeVisibleNotification")
    public static let didBecomeHiddenNotification = Notification.Name("UIWindowDidBecomeHiddenNotification")
}
