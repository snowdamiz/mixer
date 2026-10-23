import Foundation

// Original bounded fixture. The same real Wasm is used by the unmodified public
// consumer and derived counter probes, with exact storage_put/poll imports.
enum EnableReviewGuest {
    static func module(trappingStartup: Bool = false) -> Data {
        func u(_ value: Int) -> [UInt8] {
            var value = value, bytes: [UInt8] = []
            repeat { let byte = UInt8(value & 127); value >>= 7; bytes.append(byte | (value == 0 ? 0 : 128)) } while value != 0
            return bytes
        }
        func signed(_ value: Int) -> [UInt8] {
            var value = value, bytes: [UInt8] = []
            while true {
                var byte = UInt8(value & 127); value >>= 7
                let done = (value == 0 && byte & 64 == 0) || (value == -1 && byte & 64 != 0)
                if !done { byte |= 128 }; bytes.append(byte); if done { return bytes }
            }
        }
        func name(_ value: String) -> [UInt8] { u(value.utf8.count) + Array(value.utf8) }
        func section(_ tag: UInt8, _ content: [UInt8]) -> [UInt8] { [tag] + u(content.count) + content }
        func i32(_ value: Int) -> [UInt8] { [0x41] + signed(value) }
        func body(_ code: [UInt8]) -> [UInt8] { let content = [UInt8(0)] + code + [0x0b]; return u(content.count) + content }
        let arguments = Array("{\"namespace\":\"review\",\"key\":\"enabled\",\"valueBase64\":\"eWVz\"}".utf8)
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1, [3,0x60,0,0,0x60,3,0x7f,0x7f,0x7f,1,0x7f,0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f])
        bytes += section(2, [2] + name("mixer.capability.v1") + name("storage_put") + [0,1] + name("mixer.capability.v1") + name("poll") + [0,2])
        bytes += section(3, [3,0,0,0]); bytes += section(5, [1,1,1,1])
        bytes += section(7, [3] + name("startup") + [0,2] + name("run") + [0,3] + name("mixer_guest_capability_ready_v1") + [0,4])
        let run = i32(0) + i32(arguments.count) + i32(1024) + [0x10,0,0x1a]
        let ready = i32(5000) + i32(1024) + [0x29,3,0] + i32(2048) + i32(1024) + i32(4096) + [0x10,1,0x36,2,0]
        bytes += section(10, [3] + body(trappingStartup ? [0] : []) + body(run) + body(ready))
        bytes += section(11, [1,0] + i32(0) + [0x0b] + u(arguments.count) + arguments)
        return Data(bytes)
    }
}
