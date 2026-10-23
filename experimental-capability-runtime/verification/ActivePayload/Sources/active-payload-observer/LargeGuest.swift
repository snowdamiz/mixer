import Foundation

// Original bounded fixture. LEB/section encoding follows the implementer's own
// GuestProgram.swift; this variant enqueues8 gets and stores8 large wrappers.
enum LargeGuest {
    static let arguments = Data(#"{"namespace":"entries","key":"large"}"#.utf8)
    static func u(_ value: UInt32) -> [UInt8] {
        var value = value, bytes: [UInt8] = []
        repeat { let byte = UInt8(value & 127); value >>= 7; bytes.append(byte | (value == 0 ? 0 : 128)) } while value != 0
        return bytes
    }
    static func i(_ value: Int32) -> [UInt8] {
        var value = value, bytes: [UInt8] = [0x41]
        while true {
            let byte = UInt8(truncatingIfNeeded: value) & 127; value >>= 7
            let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0)
            bytes.append(byte | (done ? 0 : 128)); if done { return bytes }
        }
    }
    static func text(_ value: String) -> [UInt8] { u(UInt32(value.utf8.count)) + Array(value.utf8) }
    static func section(_ tag: UInt8, _ bytes: [UInt8]) -> [UInt8] { [tag] + u(UInt32(bytes.count)) + bytes }
    static func build() -> Data {
        let types: [[UInt8]] = [[0x60,3,0x7f,0x7f,0x7f,1,0x7f], [0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f], [0x60,0,0], [0x60,0,1,0x7f]]
        var imports = u(2)
        imports += text("mixer.capability.v1") + text("storage_get") + [0,0]
        imports += text("mixer.capability.v1") + text("poll") + [0,1]
        var run: [UInt8] = [], wake: [UInt8] = []
        for index in 0..<8 {
            run += i(1024) + i(Int32(arguments.count)) + i(Int32(16+index*8)) + [0x10,0]
            if index != 7 { run += [0x1a] }
            wake += i(Int32(16+index*8)) + [0x29,0,0] + i(Int32(131072*(index+1))) + i(131072) + i(Int32(128+4*index))
                + [0x10,1,0x45,0x04,0x40,0x23,0] + i(1) + [0x6a,0x24,0,0x0b]
        }
        run += [0x0b]; wake += [0x0b]
        let bodies: [[UInt8]] = [[0x0b], run, wake, [0x23,0,0x0b]]
        var code = u(4)
        for body in bodies { code += u(UInt32(body.count+1)) + [0] + body }
        var exports = u(4)
        for (name,index) in [("boot",2),("run",3),("mixer_guest_capability_ready_v1",4),("stage",5)] { exports += text(name) + [0] + u(UInt32(index)) }
        return Data([0,97,115,109,1,0,0,0] + section(1,u(4)+types.flatMap{$0}) + section(2,imports)
            + section(3,[4,2,3,2,3]) + section(5,[1,1,32,64]) + section(6,[1,0x7f,1,0x41,0,0x0b])
            + section(7,exports) + section(10,code) + section(11,u(1)+[0]+i(1024)+[0x0b]+u(UInt32(arguments.count))+arguments))
    }
}
