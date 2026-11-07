/// A value token, never a pointer. All three fields must match the owning registry.
public struct ResourceHandle: Codable, Hashable, Sendable {
    public let owner: String
    public let slot: UInt64
    public let generation: UInt64

    public init(owner: String, slot: UInt64, generation: UInt64) {
        self.owner = owner
        self.slot = slot
        self.generation = generation
    }
}

public enum ResourceError: Error, Equatable, Sendable {
    case invalidOwner
    case staleHandle
    case capacityExceeded
    case registryClosed
}

/// Host-owned resources with bounded capacity and reuse-safe handles. The owner ID must
/// be unique for the lifetime of the host session and must not be supplied by a guest.
public actor ResourceRegistry<Resource: Sendable> {
    private struct Slot: Sendable {
        var generation: UInt64
        var resource: Resource?
    }

    public let owner: String
    public let capacity: Int
    private var slots: [Slot] = []
    private var free: [Int] = []
    private var closed = false

    public init(owner: String, capacity: Int = 1024) throws {
        guard !owner.isEmpty, owner.utf8.count <= 128 else { throw ResourceError.invalidOwner }
        guard capacity > 0, capacity <= 1_000_000 else { throw ResourceError.capacityExceeded }
        self.owner = owner
        self.capacity = capacity
    }

    public func insert(_ resource: Resource) throws -> ResourceHandle {
        guard !closed else { throw ResourceError.registryClosed }
        if let index = free.popLast() {
            slots[index].generation += 1
            slots[index].resource = resource
            return ResourceHandle(owner: owner, slot: UInt64(index), generation: slots[index].generation)
        }
        guard slots.count < capacity else { throw ResourceError.capacityExceeded }
        slots.append(Slot(generation: 1, resource: resource))
        return ResourceHandle(owner: owner, slot: UInt64(slots.count - 1), generation: 1)
    }

    public func value(for handle: ResourceHandle) throws -> Resource {
        let index = try index(for: handle)
        guard let resource = slots[index].resource else { throw ResourceError.staleHandle }
        return resource
    }

    @discardableResult
    public func remove(_ handle: ResourceHandle) throws -> Resource {
        let index = try index(for: handle)
        guard let resource = slots[index].resource else { throw ResourceError.staleHandle }
        slots[index].resource = nil
        // Exhausted generations retire the slot instead of wrapping to an old token.
        if slots[index].generation < UInt64.max { free.append(index) }
        return resource
    }

    public func close() {
        closed = true
        slots.removeAll()
        free.removeAll()
    }

    private func index(for handle: ResourceHandle) throws -> Int {
        guard !closed else { throw ResourceError.registryClosed }
        guard handle.owner == owner else { throw ResourceError.invalidOwner }
        guard handle.slot < UInt64(slots.count) else { throw ResourceError.staleHandle }
        let index = Int(handle.slot)
        guard slots[index].generation == handle.generation, slots[index].resource != nil else {
            throw ResourceError.staleHandle
        }
        return index
    }
}
