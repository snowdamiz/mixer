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
let values = [TaskRecord(id: "a", title: "Inspect 🛠️", completed: true, note: "Draft محفوظ · cafe\u{301}"), TaskRecord(id: "b", title: "Repair", completed: false)]
do {
    let encoded = try JSONEncoder().encode(values)
    let restored = try JSONDecoder().decode([TaskRecord].self, from: encoded)
    try restored.forEach(validate)
    precondition(restored == values)
    for (decoded, original) in zip(restored, values) {
        precondition(decoded.title.utf8.elementsEqual(original.title.utf8))
        precondition(decoded.note.map { Array($0.utf8) } == original.note.map { Array($0.utf8) })
    }
    precondition(completion(restored) == 5_000)
    precondition(completion([]) == 0)
    var rejected = false
    do {
        try validate(TaskRecord(id: "c", title: "  ", completed: false))
    } catch ValidationError.emptyTitle {
        rejected = true
    }
    precondition(rejected)
    let invalid = Data(#"[{"id":"a","title":"Inspect","completed":"true"}]"#.utf8)
    var wrongFieldTypeRejected = false
    do {
        _ = try JSONDecoder().decode([TaskRecord].self, from: invalid)
    } catch DecodingError.typeMismatch(let type, let context) {
        wrongFieldTypeRejected = type == Bool.self && context.codingPath.last?.stringValue == "completed"
    }
    precondition(wrongFieldTypeRejected)
    let finite = try JSONEncoder().encode([1.25])
    precondition(finite == Data("[1.25]".utf8))
    var nonfiniteRejected = false
    do {
        _ = try JSONEncoder().encode([Double.infinity])
    } catch EncodingError.invalidValue(let value, _) {
        nonfiniteRejected = (value as? Double) == .infinity
    }
    precondition(nonfiniteRejected)
    print("{\"status\":\"passed\",\"completionBasisPoints\":5000,\"codableRoundTrip\":true,\"unicodePreserved\":true,\"emptyTitleRejected\":true,\"wrongFieldTypeRejected\":true,\"nonfiniteRejected\":true}")
} catch {
    fatalError("Feature probe failed: \(error)")
}
