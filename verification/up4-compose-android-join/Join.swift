import Dispatch
import Foundation
import MixerUI
@_spi(ComposeHost) import MixerAndroid

private typealias Receipt = AndroidComposePrepareReceipt
private typealias Outcome = Result<String, any Error>

/// The key is set once before the queue is published, and reads are queue-local.
private final class InstalledExecutor: @unchecked Sendable {
    let queue = DispatchQueue(label: "dev.mixer.verification.up4")
    private let key = DispatchSpecificKey<Bool>()

    init() { queue.setSpecific(key: key, value: true) }

    var isCurrent: Bool { DispatchQueue.getSpecific(key: key) == true }
}

private let executor = InstalledExecutor()

private enum Step: UInt8 {
    case initial, cancel, promote, supersede, replacement, replacementRetry, replacementReadback

    var revision: UInt64 {
        switch self {
        case .initial, .replacement: .max - 3
        case .cancel, .replacementRetry: .max - 2
        case .promote, .replacementReadback: .max - 1
        case .supersede: .max
        }
    }

    var isReplacement: Bool {
        switch self {
        case .replacement, .replacementRetry, .replacementReadback: true
        default: false
        }
    }
}

private final class Producer {
    let presentation: AndroidComposePresentation<Outcome>
    private var reconciler: UIReconciler
    private var draft: String
    private var saved: String?

    init(draft: String) {
        self.draft = draft
        let validator = UIValidator(supportedTextFieldAxes: [.horizontal, .vertical], textValuePolicy: .longNoteV1)
        reconciler = UIReconciler(validator: validator)
        presentation = AndroidComposePresentation(validator: validator, isOnExecutor: { executor.isCurrent })
    }

    func prepare(_ step: Step) throws -> Data {
        let status = UINode(id: "readback", kind: .text, properties: [
            "text": .string("\(step) | Draft: \(draft) | Saved: \(saved ?? "-")"),
        ])
        let title = UINode(id: "title", kind: .textField, properties: [
            "label": .string("Title"), "value": .string(draft), "axis": .string("horizontal"),
        ], actions: [.init(id: "edit", event: .textChange)])
        let save = UINode(id: "save", kind: .button, properties: ["label": .string("Save")],
                          actions: [.init(id: "save", event: .activate)])
        let root = UINode(id: "editor", kind: .vStack, properties: ["alignment": .string("leading")],
                          children: [status, title, save])
        try reconciler.apply(UIDocument(revision: step.revision, root: root))
        let snapshot = try reconciler.currentSnapshot()
        let frame = try presentation.prepare(owner: presentation.owner, snapshot: snapshot) { [unowned self] _, action in
            // Keep the app's error within Outcome. A thrown dispatch error means
            // the routing boundary never invoked this closure.
            Result { try self.handle(action, step: step) }
        }

        var bytes = frame.receipt.testBytes
        bytes.appendInteger(UInt32(frame.snapshot.nodeCount))
        func appendIdentities(_ node: UINode) {
            bytes.appendInteger(frame.snapshot.identity(for: node.id)!.generation)
            node.children.forEach(appendIdentities)
        }
        appendIdentities(frame.snapshot.document.root)
        bytes.append(frame.documentUTF8)
        return bytes
    }

    private func handle(_ action: RoutedUIAction, step: Step) throws -> String {
        if action.actionID == "edit", let value = action.value.string {
            draft = value
            return "edited"
        }
        precondition(action.actionID == "save")
        if step == .promote { throw UIRoutingError.unboundEvent }
        saved = draft
        return "save-\(step)/\(draft)"
    }
}

private enum Operation: Int32 {
    case prepare, draw, discard, offer, retire
}

private final class EditorFixture {
    private let initial = Producer(draft: "abcdef")
    private let replacement = Producer(draft: "replacement title")
    private var accepted: Receipt?

    func call(_ operation: Operation, _ data: Data) throws -> Data? {
        if operation == .prepare {
            guard data.count == 1, let step = Step(rawValue: data[0]) else { return nil }
            return try (step.isReplacement ? replacement : initial).prepare(step)
        }

        guard let receipt = Receipt(testBytes: data) else { return nil }
        let producer = producer(for: receipt)
        switch operation {
        case .draw:
            guard let producer else { return nil }
            let old: Receipt?
            switch data.count {
            case Receipt.testByteCount: old = nil
            case 2 * Receipt.testByteCount: old = Receipt(testBytes: Data(data.dropFirst(Receipt.testByteCount)))
            default: return nil
            }
            return acknowledge(receipt, on: producer, replacing: old) ? Data() : nil
        case .discard:
            guard data.count == Receipt.testByteCount,
                  producer?.presentation.cancel(receipt) == true else { return nil }
            return Data()
        case .offer:
            guard let producer else { return Data("rejected staleOwner".utf8) }
            return offer(data.dropFirst(Receipt.testByteCount), from: receipt, on: producer)
        case .retire:
            guard data.count == Receipt.testByteCount, receipt == accepted, let producer,
                  producer.presentation.retire(owner: receipt.owner) else { return nil }
            accepted = nil
            return Data()
        case .prepare:
            return nil
        }
    }

    private func producer(for receipt: Receipt) -> Producer? {
        [initial, replacement].first { $0.presentation.owner == receipt.owner }
    }

    private func acknowledge(_ receipt: Receipt, on next: Producer, replacing old: Receipt?) -> Bool {
        let previous = accepted?.owner == receipt.owner ? nil : accepted
        guard old == previous, next.presentation.acknowledgeDraw(receipt) else { return false }
        if let old {
            // The echo matched the accepted receipt on this serial executor. No call can
            // retire that lifetime between the comparison and the successful new draw.
            precondition(producer(for: old)?.presentation.retire(owner: old.owner) == true)
        }
        accepted = receipt
        return true
    }

    private func offer(_ event: Data.SubSequence, from receipt: Receipt, on producer: Producer) -> Data {
        guard let envelope = try? JSONDecoder().decode(UIEventEnvelope.self, from: event) else {
            return Data("rejected malformedJSON".utf8)
        }
        do {
            let outcome = try producer.presentation.dispatch(envelope, from: receipt)
            switch outcome {
            case .success(let value): return Data("admitted success \(value)".utf8)
            case .failure(let error): return Data("admitted failure \(error)".utf8)
            }
        } catch {
            return Data("rejected \(error)".utf8)
        }
    }

    func close() {
        for producer in [initial, replacement] {
            producer.presentation.retire(owner: producer.presentation.owner)
        }
        accepted = nil
    }
}

/// Test-only framing. The document and event bytes are their original SDK payloads.
private extension Receipt {
    static var testByteCount: Int { 48 }

    var testBytes: Data {
        var bytes = withUnsafeBytes(of: owner.uuid) { Data($0) }
        bytes.appendInteger(sequence)
        bytes.appendInteger(documentRevision)
        withUnsafeBytes(of: opaqueID.uuid) { bytes.append(contentsOf: $0) }
        return bytes
    }

    init?(testBytes bytes: Data) {
        guard bytes.count >= Self.testByteCount else { return nil }
        self = bytes.withUnsafeBytes {
            Self(owner: UUID(uuid: $0.loadUnaligned(fromByteOffset: 0, as: uuid_t.self)),
                 sequence: UInt64(bigEndian: $0.loadUnaligned(fromByteOffset: 16, as: UInt64.self)),
                 documentRevision: UInt64(bigEndian: $0.loadUnaligned(fromByteOffset: 24, as: UInt64.self)),
                 opaqueID: UUID(uuid: $0.loadUnaligned(fromByteOffset: 32, as: uuid_t.self)))
        }
    }
}

private extension Data {
    mutating func appendInteger<T: FixedWidthInteger>(_ value: T) {
        Swift.withUnsafeBytes(of: value.bigEndian) { append(contentsOf: $0) }
    }
}

// These fixture handlers link to the unmodified S5 editor_jni.c on macOS and Android.
@_cdecl("mixer_compose_editor_open_v1")
public func openEditor() -> UnsafeMutableRawPointer {
    executor.queue.sync { Unmanaged.passRetained(EditorFixture()).toOpaque() }
}

@_cdecl("mixer_compose_editor_close_v1")
public func closeEditor(_ handle: UnsafeMutableRawPointer) {
    executor.queue.sync { Unmanaged<EditorFixture>.fromOpaque(handle).takeRetainedValue().close() }
}

@_cdecl("mixer_compose_editor_call_v1")
public func callEditor(_ handle: UnsafeMutableRawPointer, _ operation: Int32,
                       _ input: UnsafePointer<UInt8>, _ count: Int,
                       _ output: UnsafeMutablePointer<UInt8>, _ capacity: Int) -> Int32 {
    guard let operation = Operation(rawValue: operation),
          (0...8192).contains(count), capacity == 8192 else { return -1 }
    return executor.queue.sync {
        let fixture = Unmanaged<EditorFixture>.fromOpaque(handle).takeUnretainedValue()
        guard let bytes = try? fixture.call(operation, Data(bytes: input, count: count)),
              bytes.count <= capacity else { return -1 }
        bytes.copyBytes(to: output, count: bytes.count)
        return Int32(bytes.count)
    }
}
