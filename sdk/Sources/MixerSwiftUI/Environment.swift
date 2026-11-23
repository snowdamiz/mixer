import MixerUI

public enum ColorScheme: CaseIterable, Hashable, Sendable {
    case light
    case dark
}

public enum LayoutDirection: CaseIterable, Hashable, Sendable {
    case leftToRight
    case rightToLeft
}

public struct EnvironmentValues: Sendable {
    public let colorScheme: ColorScheme
    public let layoutDirection: LayoutDirection

    public init() {
        colorScheme = .light
        layoutDirection = .leftToRight
    }

    init(resolved: UIAppearanceEnvironmentV2) {
        colorScheme = switch resolved.scheme {
        case .light: .light
        case .dark: .dark
        }
        layoutDirection = switch resolved.direction {
        case .leftToRight: .leftToRight
        case .rightToLeft: .rightToLeft
        }
    }
}

@propertyWrapper
public struct Environment<Value> {
    // Store only built-in accessors. Evaluation rejects other key paths before body.
    private let keyPath: KeyPath<EnvironmentValues, Value>
    let isSupported: Bool
    let identity = EnvironmentDeclarationIdentity()

    public init(_ keyPath: KeyPath<EnvironmentValues, Value>) where Value == ColorScheme {
        self.keyPath = \.colorScheme
        isSupported = keyPath == self.keyPath
    }

    public init(_ keyPath: KeyPath<EnvironmentValues, Value>) where Value == LayoutDirection {
        self.keyPath = \.layoutDirection
        isSupported = keyPath == self.keyPath
    }

    public var wrappedValue: Value {
        guard let turn = StateTurn.active, turn.scope?.contains(identity) == true else {
            return EnvironmentValues()[keyPath: keyPath]
        }
        return turn.environment[keyPath: keyPath]
    }
}

extension Environment: EnvironmentDeclaration {}

protocol EnvironmentDeclaration {
    var isSupported: Bool { get }
    var identity: EnvironmentDeclarationIdentity { get }
}

/// Copies of an authored view share the declaration. Each turn binds it anew.
final class EnvironmentDeclarationIdentity: Hashable {
    static func == (lhs: EnvironmentDeclarationIdentity, rhs: EnvironmentDeclarationIdentity) -> Bool { lhs === rhs }
    func hash(into hasher: inout Hasher) { hasher.combine(ObjectIdentifier(self)) }
}
