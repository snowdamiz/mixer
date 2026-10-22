// Independently authored model semantics probe. This is not FieldLog acceptance.
import Foundation

struct TaskRecord: Codable, Equatable {
    let id: String
    var title: String
    var completed: Bool
    var note: String?
}
enum ValidationError: Error { case emptyTitle }
func validate(_ value: TaskRecord) throws {
    guard !value.title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw ValidationError.emptyTitle }
}
func completion(_ values: [TaskRecord]) -> Int {
    values.isEmpty ? 0 : values.filter(\.completed).count * 10_000 / values.count
}
let values = [TaskRecord(id: "a", title: "Inspect 🛠️", completed: true, note: "Draft محفوظ"), TaskRecord(id: "b", title: "Repair", completed: false)]
do {
    let encoded = try JSONEncoder().encode(values)
    let restored = try JSONDecoder().decode([TaskRecord].self, from: encoded)
    try restored.forEach(validate)
    precondition(restored == values)
    precondition(completion(restored) == 5_000)
    precondition(completion([]) == 0)
    var rejected = false
    do { try validate(TaskRecord(id: "c", title: "  ", completed: false)) } catch { rejected = true }
    precondition(rejected)
    print("{\"status\":\"passed\",\"completionBasisPoints\":5000,\"codableRoundTrip\":true,\"unicodePreserved\":true,\"emptyTitleRejected\":true}")
} catch {
    fatalError("Feature probe failed: \(error)")
}
