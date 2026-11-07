import Foundation
import MixerUI

public enum AndroidBridgeError: Error {
  case invalidEvent, invalidHandle, outputLimit, revisionExhausted, taskLimit
}
public struct RenderPacket: Encodable, Sendable {
  public let schemaVersion: Int
  public let document: MixerUI.UIDocument
  public let identities: [UINodeIdentity]
}
public struct ChecklistTask: Equatable, Sendable {
  public let id: Int
  public var title: String
  public var done: Bool
}
public struct ChecklistState: Equatable, Sendable {
  public var title = "Release checklist"
  public var draft = ""
  public var tasks = [
    ChecklistTask(id: 1, title: "Verify native input", done: false),
    ChecklistTask(id: 2, title: "Review checklist", done: false),
  ]
  public var nextID = 3
}
/// This Swift model owns all example behavior. Java only renders and forwards events.
public struct ChecklistEngine: Sendable {
  public private(set) var state = ChecklistState()
  public private(set) var revision: UInt64 = 1
  private var reconciler = UIReconciler()
  public init() throws { try reconciler.apply(Self.document(state, revision: revision)) }
  public func render() throws -> Data { try Self.encode(reconciler.currentSnapshot()) }
  public mutating func dispatch(_ data: Data) throws -> Data {
    guard data.count <= 131_072 else { throw AndroidBridgeError.invalidEvent }
    try EventWireGuard.validate(data)
    let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]
    guard let object, Set(object.keys) == ["revision", "identity", "event", "value"],
      let identity = object["identity"] as? [String: Any],
      Set(identity.keys) == ["id", "generation"]
    else { throw AndroidBridgeError.invalidEvent }
    let envelope = try JSONDecoder().decode(UIEventEnvelope.self, from: data)
    let action = try reconciler.currentSnapshot().route(envelope)
    var candidate = state
    switch (action.actionID, action.value) {
    case ("title.change", .string(let value)): candidate.title = value
    case ("draft.change", .string(let value)): candidate.draft = value
    case ("task.add", .null):
      let title = candidate.draft.trimmingCharacters(in: .whitespacesAndNewlines)
      guard !title.isEmpty, candidate.tasks.count < 100 else { throw AndroidBridgeError.taskLimit }
      candidate.tasks.append(ChecklistTask(id: candidate.nextID, title: title, done: false))
      candidate.nextID += 1
      candidate.draft = ""
    case ("task.toggle", .bool(let done)):
      guard let task = candidate.tasks.firstIndex(where: { "task.\($0.id)" == action.nodeID })
      else { throw AndroidBridgeError.invalidEvent }
      candidate.tasks[task].done = done
    case ("task.reverse", .null): candidate.tasks.reverse()
    default: throw AndroidBridgeError.invalidEvent
    }
    guard revision < UInt64.max else { throw AndroidBridgeError.revisionExhausted }
    var next = reconciler
    try next.apply(Self.document(candidate, revision: revision + 1))
    let output = try Self.encode(next.currentSnapshot())
    state = candidate
    revision += 1
    reconciler = next
    return output
  }
  private static func encode(_ snapshot: UIRenderSnapshot) throws -> Data {
    do { return try snapshot.encodeNativePacketV1() }
    catch UINativePacketEncodingError.outputLimit { throw AndroidBridgeError.outputLimit }
    catch UINativePacketEncodingError.missingIdentity { throw AndroidBridgeError.invalidEvent }
  }
  private static func document(_ state: ChecklistState, revision: UInt64) -> MixerUI.UIDocument {
    MixerUI.Navigation("screen", title: "Mixer · Android") {
      MixerUI.List("checklist") {
        MixerUI.Section("editor", title: "Swift-owned checklist") {
          MixerUI.TextField("title", "Project title", value: state.title, action: "title.change")
            .accessibilityIdentifier("mixer.title")
          MixerUI.Text("heading", state.title, style: .title)
          MixerUI.Text(
            "summary", "\(state.tasks.filter(\.done).count) of \(state.tasks.count) complete",
            style: .caption)
          MixerUI.TextField(
            "draft", "New task", value: state.draft, action: "draft.change", onSubmit: "task.add"
          ).accessibilityIdentifier("mixer.draft")
          MixerUI.Button("add", "Add task", action: "task.add").disabled(
            state.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
              || state.tasks.count >= 100)
        }
        MixerUI.Section("tasks", title: "Tasks") {
          for task in state.tasks {
            MixerUI.Toggle("task.\(task.id)", task.title, value: task.done, action: "task.toggle")
              .accessibilityIdentifier("mixer.task.\(task.id)")
          }
        }
        MixerUI.Button("reverse", "Reverse task order", action: "task.reverse")
      }
    }.document(revision: revision)
  }
}

/// Reject ambiguous duplicate object keys and excessive nesting before Foundation decoding.
private struct EventWireGuard {
  let bytes: [UInt8]
  var index = 0
  static func validate(_ data: Data) throws {
    var guarder = Self(bytes: Array(data))
    try guarder.value(depth: 0)
    guarder.space()
    guard guarder.index == guarder.bytes.count else { throw AndroidBridgeError.invalidEvent }
  }
  mutating func space() {
    while index < bytes.count && [9, 10, 13, 32].contains(bytes[index]) { index += 1 }
  }
  mutating func string() throws -> String {
    guard index < bytes.count, bytes[index] == 34 else { throw AndroidBridgeError.invalidEvent }
    let start = index
    index += 1
    while index < bytes.count {
      let byte = bytes[index]
      index += 1
      if byte == 34 {
        return try JSONDecoder().decode(String.self, from: Data(bytes[start..<index]))
      }
      if byte == 92 {
        guard index < bytes.count else { throw AndroidBridgeError.invalidEvent }
        index += 1
      }
    }
    throw AndroidBridgeError.invalidEvent
  }
  mutating func value(depth: Int) throws {
    guard depth <= 8 else { throw AndroidBridgeError.invalidEvent }
    space()
    guard index < bytes.count else { throw AndroidBridgeError.invalidEvent }
    if bytes[index] == 34 {
      _ = try string()
      return
    }
    if bytes[index] == 123 {
      index += 1
      space()
      var keys = Set<String>()
      if index < bytes.count && bytes[index] == 125 {
        index += 1
        return
      }
      while true {
        space()
        let key = try string()
        guard keys.insert(key).inserted, keys.count <= 16 else {
          throw AndroidBridgeError.invalidEvent
        }
        space()
        guard index < bytes.count, bytes[index] == 58 else { throw AndroidBridgeError.invalidEvent }
        index += 1
        try value(depth: depth + 1)
        space()
        guard index < bytes.count else { throw AndroidBridgeError.invalidEvent }
        let byte = bytes[index]
        index += 1
        if byte == 125 { return }
        guard byte == 44 else { throw AndroidBridgeError.invalidEvent }
      }
    }
    guard bytes[index] != 91 else { throw AndroidBridgeError.invalidEvent }
    let start = index
    while index < bytes.count && ![9, 10, 13, 32, 44, 125].contains(bytes[index]) { index += 1 }
    guard index > start else { throw AndroidBridgeError.invalidEvent }
  }
}
