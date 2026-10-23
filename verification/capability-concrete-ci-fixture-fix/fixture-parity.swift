import Foundation
enum Before {
    static func wasm(badInitialData: Bool = false) -> Data {
        func u(_ n: Int) -> [UInt8] { var n = n, out: [UInt8] = []; repeat { let b = UInt8(n & 127); n >>= 7; out.append(b | (n == 0 ? 0 : 128)) } while n != 0; return out }
        func signed(_ n: Int) -> [UInt8] {
            var n = n, out: [UInt8] = []
            while true { var b = UInt8(n & 127); n >>= 7; let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0); if !done { b |= 128 }; out.append(b); if done { return out } }
        }
        func i(_ n: Int) -> [UInt8] { [0x41] + signed(n) }
        func name(_ s: String) -> [UInt8] { u(s.utf8.count) + Array(s.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u(bytes.count) + bytes }
        func body(_ code: [UInt8]) -> [UInt8] { let c = [UInt8(0)] + code + [0x0b]; return u(c.count) + c }
        let args = Array("{\"namespace\":\"material_test\",\"key\":\"concrete\",\"valueBase64\":\"b2s=\"}".utf8)
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[4,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f,0x60,0,1,0x7f])
        bytes += section(2,[2] + name("mixer.capability.v1") + name("storage_put") + [0,1] + name("mixer.capability.v1") + name("poll") + [0,2])
        bytes += section(3,[4,0,0,0,3]); bytes += section(5,[1,1,1,1])
        bytes += section(7,[4] + name("startup") + [0,2] + name("run") + [0,3] + name("mixer_guest_capability_ready_v1") + [0,4] + name("done") + [0,5])
        let run = i(0) + i(args.count) + i(1024) + [0x10,0,0x1a]
        let wake = i(1024) + [0x29,3,0] + i(2048) + i(1024) + i(4096) + [0x10,1,0x1a]
        bytes += section(10,[4] + body([]) + body(run) + body(wake) + body(i(4096) + [0x28,2,0]))
        var data = [UInt8(badInitialData ? 2 : 1),0] + i(0) + [0x0b] + u(args.count) + args
        if badInitialData { data += [0] + i(65_536) + [0x0b,1,7] }
        bytes += section(11,data); return Data(bytes)
    }
}
enum After {
    static func wasm(badInitialData: Bool = false) -> Data {
        func u(_ n: Int) -> [UInt8] { var n = n, out: [UInt8] = []; repeat { let b = UInt8(n & 127); n >>= 7; out.append(b | (n == 0 ? 0 : 128)) } while n != 0; return out }
        func signed(_ n: Int) -> [UInt8] {
            var n = n, out: [UInt8] = []
            while true { var b = UInt8(n & 127); n >>= 7; let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0); if !done { b |= 128 }; out.append(b); if done { return out } }
        }
        func i(_ n: Int) -> [UInt8] { [0x41] + signed(n) }
        func name(_ s: String) -> [UInt8] { u(s.utf8.count) + Array(s.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u(bytes.count) + bytes }
        func body(_ code: [UInt8]) -> [UInt8] { let c = [UInt8(0)] + code + [0x0b]; return u(c.count) + c }
        let args = Array("{\"namespace\":\"material_test\",\"key\":\"concrete\",\"valueBase64\":\"b2s=\"}".utf8)
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[4,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f,0x60,0,1,0x7f])
        var imports: [UInt8] = [2]
        imports += name("mixer.capability.v1"); imports += name("storage_put"); imports += [0,1]
        imports += name("mixer.capability.v1"); imports += name("poll"); imports += [0,2]
        bytes += section(2, imports)
        bytes += section(3,[4,0,0,0,3]); bytes += section(5,[1,1,1,1])
        var exports: [UInt8] = [4]
        exports += name("startup"); exports += [0,2]; exports += name("run"); exports += [0,3]
        exports += name("mixer_guest_capability_ready_v1"); exports += [0,4]
        exports += name("done"); exports += [0,5]
        bytes += section(7, exports)
        let run = i(0) + i(args.count) + i(1024) + [0x10,0,0x1a]
        var wake = i(1024)
        wake += [0x29,3,0]; wake += i(2048); wake += i(1024); wake += i(4096); wake += [0x10,1,0x1a]
        bytes += section(10,[4] + body([]) + body(run) + body(wake) + body(i(4096) + [0x28,2,0]))
        var data = [UInt8(badInitialData ? 2 : 1),0] + i(0) + [0x0b] + u(args.count) + args
        if badInitialData { data += [0] + i(65_536) + [0x0b,1,7] }
        bytes += section(11,data); return Data(bytes)
    }
}
for flag in [false, true] {
    let before = Before.wasm(badInitialData: flag), after = After.wasm(badInitialData: flag)
    precondition(before == after)
    print("\(flag) \(after.base64EncodedString())")
}
