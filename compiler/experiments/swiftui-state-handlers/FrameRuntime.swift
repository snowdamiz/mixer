struct FrameID: Equatable {
    let feature: UInt64
    let frame: UInt64
}

struct Document {
    enum Node: Equatable {
        case text(String)
        case button(String, handler: Int)
    }

    let id: FrameID
    let nodes: [Node]
}

final class Render {
    let state: StateStore
    private(set) var nodes: [Document.Node] = []
    private(set) var handlers: [() -> Void] = []
    private(set) var isValid = true

    init(inheriting accepted: StateStore?) {
        state = StateStore(inheriting: accepted)
    }

    func addText(_ title: String) {
        nodes.append(.text(title))
    }

    func addButton(_ title: String, action: @escaping () -> Void) {
        nodes.append(.button(title, handler: handlers.count))
        handlers.append(action)
    }

    func reject() {
        isValid = false
    }
}

// The owner calls this synchronously on a single executor. Feature closures
// receive state bindings and have no entry point back into frame management.
final class FrameRuntime {
    private struct Frame {
        let document: Document
        let state: StateStore
        let handlers: [() -> Void]
    }

    private var feature: UInt64
    private var sequence: UInt64 = 0
    private var candidate: Frame?
    private var accepted: Frame?

    init(feature: UInt64) {
        self.feature = feature
    }

    var presented: Document? { accepted?.document }

    func stage(_ view: some View) -> Document? {
        candidate = nil
        guard sequence < UInt64.max else { return nil }
        sequence += 1
        let id = FrameID(feature: feature, frame: sequence)
        let render = Render(inheriting: accepted?.state)
        view.collect(in: render, at: ViewPath())
        render.state.finish()
        guard render.isValid, render.state.isValid else { return nil }
        let document = Document(id: id, nodes: render.nodes)
        candidate = Frame(document: document, state: render.state, handlers: render.handlers)
        return document
    }

    @discardableResult
    func acknowledge(_ id: FrameID) -> Bool {
        guard let frame = candidate, frame.document.id == id else { return false }
        accepted = frame
        candidate = nil
        return true
    }

    @discardableResult
    func discard(_ id: FrameID) -> Bool {
        guard candidate?.document.id == id else { return false }
        candidate = nil
        return true
    }

    @discardableResult
    func dispatch(_ id: FrameID, handler: Int) -> Bool {
        guard let accepted, accepted.document.id == id,
              accepted.handlers.indices.contains(handler) else { return false }
        // An accepted action can change the state from which a pending frame was built.
        candidate = nil
        accepted.state.dispatch(accepted.handlers[handler])
        return true
    }

    // The host assigns a new epoch, including when it restores an earlier release.
    func replaceFeature(with successor: UInt64) -> Bool {
        guard successor > feature else { return false }
        feature = successor
        sequence = 0
        candidate = nil
        accepted = nil
        return true
    }
}
