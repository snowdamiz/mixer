import Foundation
public struct Entry: Codable, Equatable, Identifiable, Sendable {
    public let id: UUID
    public var title: String
    public var note: String
    public var completed: Bool
    public init(id: UUID = UUID(), title: String, note: String = "", completed: Bool = false) {
        self.id = id; self.title = title; self.note = note; self.completed = completed
    }
    public var isValid: Bool { !title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
}
public enum ProjectProgress {
    public static func fraction(_ entries: [Entry]) -> Double {
        entries.isEmpty ? 0 : Double(entries.filter(\.completed).count) / Double(entries.count)
    }
}
