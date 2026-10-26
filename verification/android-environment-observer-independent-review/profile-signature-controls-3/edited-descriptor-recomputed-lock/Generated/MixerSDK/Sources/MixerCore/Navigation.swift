import Foundation

public struct NavigationRoute: Codable, Equatable, Sendable, Identifiable {
    public let id: String
    public let name: String
    public let parameters: [String: String]

    public init(id: String, name: String, parameters: [String: String] = [:]) {
        self.id = id
        self.name = name
        self.parameters = parameters
    }
}

public enum NavigationError: Error, Equatable, Sendable {
    case unsupportedSchema(Int)
    case oversizedRepresentation
    case invalidRoute(String)
    case duplicateIdentity(String)
}

/// Restorable values contain no serialized object graph or host resources.
public struct NavigationState: Codable, Equatable, Sendable {
    public static let currentSchemaVersion = 1
    public let schemaVersion: Int
    public private(set) var routes: [NavigationRoute]

    public init(routes: [NavigationRoute] = []) throws {
        schemaVersion = Self.currentSchemaVersion
        self.routes = routes
        try validate()
    }

    public mutating func push(_ route: NavigationRoute) throws {
        let next = try NavigationState(routes: routes + [route])
        self = next
    }

    @discardableResult
    public mutating func pop() -> NavigationRoute? { routes.popLast() }

    public mutating func popToRoot() { routes.removeAll() }

    public func encoded() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        return try encoder.encode(self)
    }

    public static func restore(from data: Data, maximumBytes: Int = 262_144) throws -> NavigationState {
        guard maximumBytes > 0, data.count <= maximumBytes else {
            throw NavigationError.oversizedRepresentation
        }
        return try JSONDecoder().decode(Self.self, from: data)
    }

    public init(from decoder: any Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        schemaVersion = try values.decode(Int.self, forKey: .schemaVersion)
        routes = try values.decode([NavigationRoute].self, forKey: .routes)
        try validate()
    }

    private func validate() throws {
        guard schemaVersion == Self.currentSchemaVersion else {
            throw NavigationError.unsupportedSchema(schemaVersion)
        }
        guard routes.count <= 64 else { throw NavigationError.oversizedRepresentation }
        var ids: Set<String> = []
        for route in routes {
            guard validID(route.id), validID(route.name), route.parameters.count <= 32 else {
                throw NavigationError.invalidRoute(route.id)
            }
            guard ids.insert(route.id).inserted else { throw NavigationError.duplicateIdentity(route.id) }
            for (key, value) in route.parameters {
                guard validID(key), value.utf8.count <= 4096 else {
                    throw NavigationError.invalidRoute(route.id)
                }
            }
        }
    }

    private func validID(_ value: String) -> Bool {
        !value.isEmpty && value.utf8.count <= 128 && !value.unicodeScalars.contains { $0.value < 0x20 }
    }
}
