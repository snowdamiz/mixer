/// A feature instance starts once and is never reused after stopping.
public enum FeatureLifecycle: String, Codable, Sendable {
    case initialized, active, background, stopped
}

public enum LifecycleEvent: String, Codable, Sendable {
    case start, enterForeground, enterBackground, stop
}

public enum LifecycleError: Error, Equatable, Sendable {
    case invalidTransition(FeatureLifecycle, LifecycleEvent)
    case featureNotRunning
    case reentrantDispatch
}

extension FeatureLifecycle {
    public func applying(_ event: LifecycleEvent) throws -> FeatureLifecycle {
        switch (self, event) {
        case (.initialized, .start), (.background, .enterForeground): return .active
        case (.active, .enterBackground): return .background
        case (.initialized, .stop), (.active, .stop), (.background, .stop): return .stopped
        default: throw LifecycleError.invalidTransition(self, event)
        }
    }
}
