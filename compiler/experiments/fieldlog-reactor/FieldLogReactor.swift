// Test-only full Swift reactor boundary. This status is not a feature ABI.
import Foundation
import FieldLogModels
#if os(WASI)
import WASILibc
#else
import Darwin
#endif

struct Receipt: Encodable {
    let status = "passed"
    let taskCount: Int
    let completionBasisPoints: Int
    let codableRoundTrip: Bool
    let unicodePreserved: Bool
    let reordered: Bool
    let committedEntries: Int
    let pendingChanges: Int
    let emptyTitleRejected: Bool
    let repeatedCommitRejected: Bool
    let reportIncludesEntry: Bool
}

// The body between these braces is byte-identical to the frozen corpus body.
private func runFieldLogCorpus() throws {
let now = Date(timeIntervalSince1970: 1_792_627_200)
var workspace = Workspace(createdAt: now)
let projectID = try workspace.createProject(title: "North workshop", site: "Site A", now: now)
workspace.revision += 1
for index in 0..<1000 {
    try workspace.saveTask(projectID: projectID, title: "Inspect station \(index)", responsible: "", now: now)
    workspace.revision += 1
}
for task in workspace.tasks.prefix(500) {
    try workspace.toggleTask(task.id, now: now)
    workspace.revision += 1
}
let reversed = workspace.tasks(for: projectID).reversed().map(\.id)
try workspace.reorderTasks(projectID: projectID, ids: reversed, now: now)
workspace.revision += 1
let note = "Draft محفوظ · inspect 🛠️ · cafe\u{301}"
let draft = EntryDraft(projectID: projectID, title: "Inspection complete", note: note,
                       category: .progress, occurredAt: now, updatedAt: now)
try workspace.saveDraft(draft)
try workspace.validate()
let before = workspace
workspace = try JSONDecoder().decode(Workspace.self, from: JSONEncoder().encode(workspace))
let roundTrip = workspace == before
try workspace.commitDraft(draft.id, now: now)
workspace.revision += 1
try workspace.validate()
var emptyRejected = false
do { _ = try workspace.createProject(title: "  ", site: "", now: now) }
catch FieldLogError.validation { emptyRejected = true }
var repeatRejected = false
do { try workspace.commitDraft(draft.id, now: now) }
catch FieldLogError.missingRecord { repeatRejected = true }
let report = try workspace.report(projectID: projectID)
let result = Receipt(taskCount: workspace.tasks.count,
                     completionBasisPoints: Int(workspace.progress(for: projectID) * 10_000),
                     codableRoundTrip: roundTrip, unicodePreserved: workspace.entries.first?.note == note,
                     reordered: workspace.tasks(for: projectID).map(\.id) == reversed,
                     committedEntries: workspace.entries.count, pendingChanges: workspace.outbox.count,
                     emptyTitleRejected: emptyRejected, repeatedCommitRejected: repeatRejected,
                     reportIncludesEntry: report.contains(note) && report.contains("Inspection complete"))
precondition(result.taskCount == 1000 && result.completionBasisPoints == 5000)
precondition(result.codableRoundTrip && result.unicodePreserved && result.reordered)
precondition(result.committedEntries == 1 && result.pendingChanges == 1503)
precondition(result.emptyTitleRejected && result.repeatedCommitRejected && result.reportIncludesEntry)
let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
print(String(decoding: try encoder.encode(result), as: UTF8.self))
}

// Swift errors must not cross a C-compatible boundary. Traps are not Swift errors.
func fieldLogStatus(_ body: () throws -> Void) -> Int32 {
    do {
        try body()
        // A reactor returns without libc process exit. Deliver each original
        // print before reporting success; a failed flush is an explicit failure.
        return fflush(nil) == 0 ? 0 : 2
    } catch {
        return 1
    }
}

@_cdecl("mixer_fieldlog_corpus_v1")
public func mixerFieldLogCorpusV1() -> Int32 {
    fieldLogStatus(runFieldLogCorpus)
}
