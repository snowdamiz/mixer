struct ViewPath: Hashable {
    enum Component: Hashable {
        case view(ObjectIdentifier)
        case child(Int)
        case branch(Bool)
        case row(Int)
    }

    private var components: [Component] = []

    func appending(_ component: Component) -> Self {
        var path = self
        path.components.append(component)
        return path
    }
}

struct StateAddress: Hashable {
    let view: ViewPath
    let declaration: String
}

final class StateStore {
    private enum Phase { case evaluating, idle, dispatching }
    private var phase = Phase.evaluating
    private var inherited: [StateAddress: Any]
    private var values: [StateAddress: Any] = [:]
    private(set) var isValid = true

    init(inheriting accepted: StateStore?) {
        inherited = accepted?.values ?? [:]
    }

    func register<Value>(_ address: StateAddress, initial: Value) {
        guard values[address] == nil else {
            isValid = false
            return
        }
        if let previous = inherited[address] {
            guard previous is Value else {
                isValid = false
                return
            }
            values[address] = previous
        } else {
            values[address] = initial as Any
        }
    }

    func read<Value>(_ address: StateAddress, initial: Value) -> Value {
        values[address] as? Value ?? initial
    }

    func write<Value>(_ address: StateAddress, value: Value) {
        if phase == .evaluating { isValid = false }
        guard phase == .dispatching, values[address] is Value else { return }
        values[address] = value as Any
    }

    func finish() {
        inherited.removeAll()
        phase = .idle
    }

    func dispatch(_ action: () -> Void) {
        precondition(phase == .idle)
        phase = .dispatching
        defer { phase = .idle }
        action()
    }
}

protocol StateValue {}
extension Int: StateValue {}
extension Bool: StateValue {}

protocol StateProperty {
    func bind(_ address: StateAddress, to store: StateStore)
}

@propertyWrapper
struct State<Value: StateValue>: StateProperty {
    private final class Location {
        var address: StateAddress?
        weak var store: StateStore?
    }

    private let initial: Value
    private let location = Location()

    init(wrappedValue: Value) {
        initial = wrappedValue
    }

    var wrappedValue: Value {
        get {
            guard let address = location.address, let store = location.store else { return initial }
            return store.read(address, initial: initial)
        }
        nonmutating set {
            guard let address = location.address else { return }
            location.store?.write(address, value: newValue)
        }
    }

    var projectedValue: Binding<Value> {
        Binding(get: { wrappedValue }, set: { wrappedValue = $0 })
    }

    func bind(_ address: StateAddress, to store: StateStore) {
        precondition(location.address == nil, "Evaluate a fresh view value for each identity")
        store.register(address, initial: initial)
        location.address = address
        location.store = store
    }
}

@propertyWrapper
struct Binding<Value> {
    let get: () -> Value
    let set: (Value) -> Void

    var wrappedValue: Value {
        get { get() }
        nonmutating set { set(newValue) }
    }

    var projectedValue: Self { self }
}
