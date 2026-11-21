@propertyWrapper
private struct BoundedMeasurement {
    private var value: UInt16 = 0
    private var changes: UInt32 = 0

    var wrappedValue: UInt16 {
        get { value }
        set {
            let bounded = min(newValue, 1_000)
            if bounded != value {
                value = bounded
                changes &+= 1
            }
        }
    }

    var projectedValue: UInt32 { changes }
}

struct PropertyWrapperPreview {
    static let inputSize = 2
    static let outputSize = 8

    @BoundedMeasurement private var measurement: UInt16

    mutating func render(_ input: UnsafeRawBufferPointer, into output: UnsafeMutableRawBufferPointer) -> Bool {
        guard input.count == Self.inputSize else { return false }
        let reading = UInt16(littleEndian: input.loadUnaligned(as: UInt16.self))
        guard reading != UInt16.max else { return false }

        measurement = reading
        output.storeBytes(of: UInt32(measurement).littleEndian, as: UInt32.self)
        output.storeBytes(of: $measurement.littleEndian, toByteOffset: 4, as: UInt32.self)
        return true
    }
}
