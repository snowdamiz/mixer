import UIKit

/// One passive main-actor observer; never supplies an original identity or anchor.
@MainActor final class PassiveLifecycleObserver {
    private let buffer = PassiveLifecycleBuffer()
    private let faults = PassiveLifecycleDeliveryFaults()
    private var ownership: PassiveLifecycleOwnership?
    private let tokens = PassiveLifecycleTokens(center: .default)
    private static let notifications: [(Notification.Name, PassiveLifecycleKind)] = [
        (UIApplication.didBecomeActiveNotification, .appActive), (UIApplication.willResignActiveNotification, .appInactive),
        (UIApplication.willEnterForegroundNotification, .appForeground), (UIApplication.didEnterBackgroundNotification, .appBackground),
        (UIWindow.didBecomeKeyNotification, .windowKey), (UIWindow.didResignKeyNotification, .windowNotKey),
        (UIWindow.didBecomeVisibleNotification, .windowVisible), (UIWindow.didBecomeHiddenNotification, .windowHidden),
        (UIScene.willConnectNotification, .sceneConnect), (UIScene.didDisconnectNotification, .sceneDisconnect),
        (UIScene.didActivateNotification, .sceneActive), (UIScene.willDeactivateNotification, .sceneInactive),
        (UIScene.willEnterForegroundNotification, .sceneForeground), (UIScene.didEnterBackgroundNotification, .sceneBackground)
    ]
    func start(application: UIApplication, window: UIWindow) {
        guard ownership == nil, application === UIApplication.shared else { buffer.register(tokens: 0); return }
        ownership = PassiveLifecycleOwnership(application: application, window: window)
        for (name, kind) in Self.notifications {
            let faults = self.faults
            let token = NotificationCenter.default.addObserver(forName: name, object: nil, queue: nil) { [weak self, faults] note in
                guard Thread.isMainThread else { faults.record(); return }
                let object = note.object as AnyObject?
                let objectIdentity = object.map { PassiveLifecycleIdentity($0).value }
                withExtendedLifetime(object) {
                    MainActor.assumeIsolated { self?.notification(kind, objectIdentity: objectIdentity) }
                }
            }
            guard tokens.insert(token) else { buffer.register(tokens: 0); tokens.removeAll(); return }
        }
        buffer.register(tokens: tokens.count)
        capture(site: .registration, contextSequence: nil, kind: nil, object: nil)
    }
    func sample(site: String, contextSequence: Int?) {
        guard let site = PassiveLifecycleSite(rawValue: site), site == .snapshot || site == .controllerCallback || site == .carrierCallback else { buffer.invalidSite(); return }
        capture(site: site, contextSequence: contextSequence, kind: nil, object: nil)
    }
    private func notification(_ kind: PassiveLifecycleKind, objectIdentity: String?) {
        guard let ownership, let application = ownership.application, let window = ownership.window as? UIWindow else {
            buffer.ownershipEnded(); tokens.removeAll(); return
        }
        let currentScene = window.windowScene
        let ownedObject: AnyObject?
        switch kind.family {
        case 0: ownedObject = application
        case 1: ownedObject = window
        default: ownedObject = currentScene
        }
        guard let ownedObject, objectIdentity == PassiveLifecycleIdentity(ownedObject).value else { buffer.filteredNotification(); return }
        capture(site: .notification, contextSequence: nil, kind: kind, object: ownedObject)
    }
    private func capture(site: PassiveLifecycleSite, contextSequence: Int?, kind: PassiveLifecycleKind?, object: AnyObject?) {
        let started = ProcessInfo.processInfo.systemUptime
        guard let application = ownership?.application as? UIApplication, let window = ownership?.window as? UIWindow else {
            buffer.ownershipEnded(); tokens.removeAll(); return
        }
        let appState: PassiveLifecycleAppState
        switch application.applicationState {
        case .active: appState = .active
        case .inactive: appState = .inactive
        case .background: appState = .background
        @unknown default: appState = .unknown
        }
        let windowIdentity = PassiveLifecycleIdentity(window)
        let isKey = window.isKeyWindow
        let scene = window.windowScene
        let sceneIdentity = scene.map(PassiveLifecycleIdentity.init)
        let sceneState: PassiveLifecycleSceneState
        if let scene {
            switch scene.activationState {
            case .unattached: sceneState = .unattached
            case .foregroundActive: sceneState = .foregroundActive
            case .foregroundInactive: sceneState = .foregroundInactive
            case .background: sceneState = .background
            @unknown default: sceneState = .unknown
            }
        } else { sceneState = .absent }
        let finished = ProcessInfo.processInfo.systemUptime
        buffer.append(PassiveLifecycleSnapshot(systemUptime: started, finishedUptime: finished,
            processIdentifier: Int(ProcessInfo.processInfo.processIdentifier), site: site, contextSequence: contextSequence,
            notificationKind: kind, notificationObjectIdentity: object.map(PassiveLifecycleIdentity.init), applicationState: appState,
            ownedWindowIdentity: windowIdentity, ownedWindowIsKey: isKey, ownedWindowSceneIdentity: sceneIdentity, ownedSceneActivationState: sceneState))
    }
    var value: [String: Any] { buffer.value(offMain: faults.value) }
}
