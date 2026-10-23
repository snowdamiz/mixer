import Foundation

/// Original tiny Wasm encoder, independent of the engine's fixture builders.
struct GuestProgram {
    static let put = Data(#"{"namespace":"entries","key":"binary","valueBase64":"AAH+/w=="}"#.utf8)
    static let get = Data(#"{"namespace":"entries","key":"binary"}"#.utf8)
    enum Mode { case storage, trap, spin, single(UInt32, Data), unconsumed, burst(Int) }
    static func u(_ n: UInt32) -> [UInt8] {
        var n = n, out: [UInt8] = []
        repeat { let b = UInt8(n & 127); n >>= 7; out.append(b | (n == 0 ? 0 : 128)) } while n != 0
        return out
    }
    static func i(_ n: Int32) -> [UInt8] {
        var n = n, out: [UInt8] = [0x41]
        while true {
            let b = UInt8(truncatingIfNeeded: n) & 127; n >>= 7
            let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0)
            out.append(b | (done ? 0 : 128)); if done { return out }
        }
    }
    static func text(_ s: String) -> [UInt8] { u(UInt32(s.utf8.count)) + Array(s.utf8) }
    static func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u(UInt32(bytes.count)) + bytes }
    static func sig(_ params: [UInt8], _ result: UInt8?) -> [UInt8] { [0x60] + u(UInt32(params.count)) + params + [result == nil ? 0 : 1] + (result.map { [$0] } ?? []) }
    static func enqueue(_ operation: UInt32, _ address: Int32, _ length: Int) -> [UInt8] {
        i(address) + i(Int32(length)) + i(16) + [0x10] + u(operation)
    }
    static func build(_ mode: Mode = .storage) -> Data {
        let arg: Data
        if case .single(_, let value) = mode { arg = value } else { arg = put }
        let names = ["http_request", "storage_get", "storage_put", "storage_delete", "cancel", "poll"]
        let types = [sig([0x7f,0x7f,0x7f],0x7f), sig([0x7e,0x7f,0x7f,0x7f],0x7f), sig([0x7e],0x7f), sig([],nil), sig([],0x7f)]
        var imports = u(6)
        for (index, name) in names.enumerated() { imports += text("mixer.capability.v1") + text(name) + [0] + u(index < 4 ? 0 : index == 4 ? 2 : 1) }
        let operation: UInt32
        if case .single(let op, _) = mode { operation = op } else { operation = 2 }
        var run = i(1) + [0x24,0] + enqueue(operation, 1024, arg.count)
        if case .burst(let count) = mode {
            run = i(0) + [0x24,0]
            for index in 0..<count {
                run += i(1024) + i(Int32(arg.count)) + i(Int32(16 + index * 8)) + [0x10,2]
                if index + 1 != count { run += [0x1a] }
            }
        }
        switch mode {
        case .trap: run += [0x1a,0x00]
        case .spin: run += [0x1a,0x03,0x40,0x0c,0,0x0b,0x00]
        default: break
        }
        run += [0x0b]
        // Output per stage at 4096*stage; length words at 124+4*stage.
        var poll = i(16)
        poll += [0x29,0,0,0x23,0]
        poll += i(4096)
        poll += [0x6c]
        poll += i(2048)
        poll += [0x23,0]
        poll += i(4)
        poll += [0x6c]
        poll += i(124)
        poll += [0x6a,0x10,5]
        var wake: [UInt8]
        if case .unconsumed = mode { wake = [0x0b] }
        else if case .burst(let count) = mode {
            wake = []
            for index in 0..<count {
                wake += i(Int32(16 + index * 8))
                wake += [0x29,0,0]
                wake += i(Int32(4096*(index+1)))
                wake += i(2048)
                wake += i(Int32(128+4*index))
                wake += [0x10,5,0x45,0x04,0x40,0x23,0]
                wake += i(1)
                wake += [0x6a,0x24,0,0x0b]
            }
            wake += [0x0b]
        }
        else {
            wake = poll + [0x45,0x04,0x40]
            if case .storage = mode {
                for (stage, op) in [(1,UInt32(1)),(2,UInt32(3)),(3,UInt32(1))] {
                    wake += [0x23,0] + i(Int32(stage)) + [0x46,0x04,0x40]
                    wake += enqueue(op, 1536, get.count) + [0x1a] + i(Int32(stage+1)) + [0x24,0,0x05]
                }
                wake += i(5) + [0x24,0]
                wake += [0x0b,0x0b,0x0b]
            } else { wake += i(5) + [0x24,0] }
            wake += [0x0b,0x0b]
        }
        let bodies: [[UInt8]] = [[0x0b], run, wake, [0x23,0,0x0b]]
        var exports = u(4)
        for (name,index) in [("boot",6),("run",7),("mixer_guest_capability_ready_v1",8),("stage",9)] { exports += text(name) + [0] + u(UInt32(index)) }
        var code = u(UInt32(bodies.count))
        for b in bodies { let body = [UInt8(0)] + b; code += u(UInt32(body.count)) + body }
        var data = u(2)
        for (offset, bytes) in [(Int32(1024),arg),(Int32(1536),get)] { data += [0] + i(offset) + [0x0b] + u(UInt32(bytes.count)) + bytes }
        var module: [UInt8] = [0,97,115,109,1,0,0,0]
        module += section(1,u(UInt32(types.count)) + types.flatMap { $0 })
        module += section(2,imports)
        module += section(3,[4,3,4,3,4])
        module += section(5,[1,1,10,64])
        module += section(6,[1,0x7f,1,0x41,0,0x0b])
        module += section(7,exports)
        module += section(10,code)
        module += section(11,data)
        return Data(module)
    }
}
