struct TaskCompletion {
    private(set) var completed = false
    private(set) var reviewPending = false
    private(set) var revision: UInt64 = 1

    mutating func activate(requireReview: Bool) -> Bool {
        guard revision < UInt64.max else { return false }
        if requireReview && !completed && !reviewPending {
            reviewPending = true
        } else {
            completed.toggle()
            reviewPending = false
        }
        revision += 1
        return true
    }

    func accepts(_ input: UnsafeRawBufferPointer) -> Bool {
        var event = WireBytes(input)
        // UI v1 delivers canonical bytes from GuestUIEventCodecV1 for this fixed route.
        return event.consume(#"{"actionID":"task.toggle","event":"activate","nodeID":"toggle","revision":"#)
            && event.consume(revision)
            && event.consume(#","schemaVersion":1,"sequence":"#)
            && event.consume(revision)
            && event.consume(#","value":null}"#)
            && event.atEnd
    }

    func render(into destination: UnsafeMutableRawBufferPointer) -> Int {
        var document = WireWriter(destination)
        document.append(#"{"schemaVersion":1,"revision":"#)
        document.append(revision)
        document.append(#","root":{"id":"fieldlog-task","kind":"vStack","properties":{},"actions":[],"children":["#)
        document.append(#"{"id":"task","kind":"text","properties":{"text":"Inspect pump"},"children":[],"actions":[]},"#)
        document.append(#"{"id":"status","kind":"text","properties":{"text":""#)
        document.append(completed ? "Completed" : reviewPending ? "Review required" : "Open")
        document.append(#""},"children":[],"actions":[]},"#)
        document.append(#"{"id":"toggle","kind":"button","properties":{"label":""#)
        document.append(completed ? "Reopen task" : reviewPending ? "Confirm completion" : "Complete task")
        document.append(#""},"children":[],"actions":[{"id":"task.toggle","event":"activate"}]}]}}"#)
        return document.count
    }
}

private struct WireBytes {
    var atEnd: Bool { remaining.isEmpty }
    private var remaining: UnsafeRawBufferPointer

    init(_ bytes: UnsafeRawBufferPointer) { remaining = bytes }

    mutating func consume(_ text: StaticString) -> Bool {
        for index in 0..<text.utf8CodeUnitCount {
            guard let byte = next(), byte == text.utf8Start[index] else { return false }
        }
        return true
    }

    mutating func consume(_ number: UInt64) -> Bool {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            guard let byte = next(), byte == digit(number, divisor: divisor) else { return false }
            divisor /= 10
        }
        return true
    }

    private mutating func next() -> UInt8? {
        guard let address = remaining.baseAddress, !remaining.isEmpty else { return nil }
        let byte = remaining[0]
        remaining = UnsafeRawBufferPointer(start: address + 1, count: remaining.count - 1)
        return byte
    }
}

private struct WireWriter {
    private var destination: UnsafeMutableRawBufferPointer
    private(set) var count = 0

    init(_ destination: UnsafeMutableRawBufferPointer) { self.destination = destination }

    mutating func append(_ text: StaticString) {
        for index in 0..<text.utf8CodeUnitCount { append(text.utf8Start[index]) }
    }

    mutating func append(_ number: UInt64) {
        var divisor = decimalDivisor(number)
        while divisor > 0 {
            append(digit(number, divisor: divisor))
            divisor /= 10
        }
    }

    private mutating func append(_ byte: UInt8) {
        precondition(count < destination.count)
        destination[count] = byte
        count += 1
    }
}

private func decimalDivisor(_ number: UInt64) -> UInt64 {
    var divisor: UInt64 = 1
    // The quotient check guarantees the product is at most number.
    while number / divisor >= 10 { divisor &*= 10 }
    return divisor
}

private func digit(_ number: UInt64, divisor: UInt64) -> UInt8 {
    UInt8((number / divisor) % 10) + 48
}
