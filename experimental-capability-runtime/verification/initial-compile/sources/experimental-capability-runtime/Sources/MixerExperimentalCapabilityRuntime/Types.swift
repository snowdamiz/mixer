import Foundation
import CMixerVMCapability

/// Experimental native configuration only; this is not release/activation authority.
public struct ExperimentalCapabilityConfiguration: Sendable {
    public let fuel: UInt64
    public let memoryPages: UInt32
    public let operandStack: UInt32
    public let callDepth: UInt32
    public let hostCalls: UInt32
    public let maximumRequests: UInt32
    public let reservationBytes: UInt64
    public let timeoutMilliseconds: UInt32
    public let turnMilliseconds: UInt32
    public let dispatchBurst: UInt32
    public let dispatchesPerSecond: UInt32
    public let batchTurns: UInt32
    public let batchMilliseconds: UInt32
    public init(fuel: UInt64 = 1_000_000, memoryPages: UInt32 = 64, operandStack: UInt32 = 4096,
                callDepth: UInt32 = 64, hostCalls: UInt32 = 1024, maximumRequests: UInt32 = 8,
                reservationBytes: UInt64 = 8_388_608, timeoutMilliseconds: UInt32 = 30000,
                turnMilliseconds: UInt32 = 50, dispatchBurst: UInt32 = 8,
                dispatchesPerSecond: UInt32 = 32, batchTurns: UInt32 = 4,
                batchMilliseconds: UInt32 = 8) {
        self.fuel = fuel; self.memoryPages = memoryPages; self.operandStack = operandStack
        self.callDepth = callDepth; self.hostCalls = hostCalls; self.maximumRequests = maximumRequests
        self.reservationBytes = reservationBytes; self.timeoutMilliseconds = timeoutMilliseconds
        self.turnMilliseconds = turnMilliseconds; self.dispatchBurst = dispatchBurst
        self.dispatchesPerSecond = dispatchesPerSecond; self.batchTurns = batchTurns
        self.batchMilliseconds = batchMilliseconds
    }
    func validate() throws {
        guard (1...1_000_000).contains(fuel), (1...64).contains(memoryPages),
              (1...4096).contains(operandStack), (1...64).contains(callDepth), hostCalls <= 1024,
              (1...8).contains(maximumRequests), (1...8_388_608).contains(reservationBytes),
              (1...30000).contains(timeoutMilliseconds), (1...50).contains(turnMilliseconds),
              (1...8).contains(dispatchBurst), (1...32).contains(dispatchesPerSecond),
              (1...4).contains(batchTurns), (1...8).contains(batchMilliseconds) else {
            throw ExperimentalCapabilityError("invalid_configuration")
        }
    }
    var vm: MixerVmLimits {
        MixerVmLimits(struct_size: 32, abi_version: 1, fuel: fuel, memory_pages: memoryPages,
                      operand_stack: operandStack, call_depth: callDepth, host_calls: hostCalls)
    }
    var capability: MixerVmCapabilityLimitsV1 {
        MixerVmCapabilityLimitsV1(struct_size: 32, abi_version: 1, maximum_requests: maximumRequests,
                                 timeout_milliseconds: timeoutMilliseconds, turn_milliseconds: turnMilliseconds,
                                 reserved: 0, reservation_bytes: reservationBytes)
    }
}

public struct ExperimentalCapabilityError: Error, Sendable, Equatable, CustomStringConvertible {
    public let code: String
    public let nativeStatus: UInt32?
    public var description: String { code }
    init(_ code: String, status: UInt32? = nil) { self.code = code; nativeStatus = status }
}
public enum ExperimentalVMValue: Sendable, Equatable {
    case i32(Int32), i64(Int64), f32Bits(UInt32), f64Bits(UInt64)
    var native: MixerVmValue {
        switch self {
        case .i32(let v): MixerVmValue(value_type: 1, reserved: 0, value: Int64(v))
        case .i64(let v): MixerVmValue(value_type: 2, reserved: 0, value: v)
        case .f32Bits(let v): MixerVmValue(value_type: 3, reserved: 0, value: Int64(v))
        case .f64Bits(let v): MixerVmValue(value_type: 4, reserved: 0, value: Int64(bitPattern: v))
        }
    }
}
public struct ExperimentalCapabilityInvocation: Sendable, Equatable {
    public let value: ExperimentalVMValue?
    public let fuelUsed: UInt64
    public let hostCallsUsed: UInt64
}
public struct ExperimentalCapabilityStatus: Sendable, Equatable {
    public internal(set) var closed = false
    public internal(set) var drained = false
    public internal(set) var retainedExits = 0
    public internal(set) var retainedPayloadBytes = 0
    public internal(set) var turns: UInt64 = 0
    public internal(set) var yields: UInt64 = 0
    public internal(set) var timerTicks: UInt64 = 0
    public internal(set) var acceptedCalls: UInt64 = 0
    public internal(set) var acknowledgements: UInt64 = 0
    public internal(set) var maximumBatchTurns = 0
    public internal(set) var failure: String?
}
