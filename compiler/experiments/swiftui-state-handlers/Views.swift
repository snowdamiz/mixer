protocol View {
    associatedtype Body: View
    @ViewBuilder var body: Body { get }
    func collectContents(in render: Render, at path: ViewPath)
}

extension View {
    func collect(in render: Render, at path: ViewPath) {
        if Self.self is any CustomReflectable.Type {
            render.reject()
            return
        }
        collectContents(in: render, at: path)
    }

    func collectContents(in render: Render, at path: ViewPath) {
        let identity = path.appending(.view(ObjectIdentifier(Self.self)))
        for child in Mirror(reflecting: self).children {
            guard let property = child.value as? any StateProperty else { continue }
            guard let declaration = child.label else {
                render.reject()
                return
            }
            property.bind(StateAddress(view: identity, declaration: declaration), to: render.state)
        }
        body.collect(in: render, at: identity)
    }
}

protocol PrimitiveView: View where Body == Never {}

extension PrimitiveView {
    var body: Never { fatalError("A primitive view renders directly") }
}

extension Never: View {
    typealias Body = Never

    var body: Never { return fatalError("Never has no body") }
    func collectContents(in render: Render, at path: ViewPath) {}
}

@resultBuilder
enum ViewBuilder {
    static func buildBlock(_ children: any View...) -> ViewGroup {
        ViewGroup(children: children)
    }

    static func buildEither(first: ViewGroup) -> Branch {
        Branch(content: first, first: true)
    }

    static func buildEither(second: ViewGroup) -> Branch {
        Branch(content: second, first: false)
    }

    static func buildOptional(_ content: ViewGroup?) -> Branch {
        Branch(content: content, first: true)
    }
}

struct ViewGroup: PrimitiveView {
    let children: [any View]

    func collectContents(in render: Render, at path: ViewPath) {
        for (index, child) in children.enumerated() {
            child.collect(in: render, at: path.appending(.child(index)))
        }
    }
}

struct Branch: PrimitiveView {
    let content: ViewGroup?
    let first: Bool

    func collectContents(in render: Render, at path: ViewPath) {
        content?.collect(in: render, at: path.appending(.branch(first)))
    }
}

struct VStack: PrimitiveView {
    private let content: ViewGroup

    init(@ViewBuilder content: () -> ViewGroup) {
        self.content = content()
    }

    func collectContents(in render: Render, at path: ViewPath) {
        content.collect(in: render, at: path.appending(.view(ObjectIdentifier(Self.self))))
    }
}

struct Text: PrimitiveView {
    let title: String
    init(_ title: String) { self.title = title }

    func collectContents(in render: Render, at path: ViewPath) {
        render.addText(title)
    }
}

struct Button: PrimitiveView {
    let title: String
    let action: () -> Void

    init(_ title: String, action: @escaping () -> Void) {
        self.title = title
        self.action = action
    }

    func collectContents(in render: Render, at path: ViewPath) {
        render.addButton(title, action: action)
    }
}

struct ForEach<Element>: PrimitiveView {
    let data: [Element]
    let id: KeyPath<Element, Int>
    let content: (Element) -> ViewGroup

    init(_ data: [Element], id: KeyPath<Element, Int>, @ViewBuilder content: @escaping (Element) -> ViewGroup) {
        self.data = data
        self.id = id
        self.content = content
    }

    func collectContents(in render: Render, at path: ViewPath) {
        let identity = path.appending(.view(ObjectIdentifier(Self.self)))
        var keys: Set<Int> = []
        for row in data {
            let key = row[keyPath: id]
            guard keys.insert(key).inserted else {
                render.reject()
                return
            }
            content(row).collect(in: render, at: identity.appending(.row(key)))
        }
    }
}
