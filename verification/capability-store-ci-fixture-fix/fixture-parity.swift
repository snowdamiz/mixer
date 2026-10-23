import Foundation
enum Old {
    static func wasm(invalidUncalled: Bool = false, memoryPages: UInt8 = 0) -> Data {
        func name(_ value: String) -> [UInt8] { [UInt8(value.utf8.count)] + Array(value.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id, UInt8(bytes.count)] + bytes }
        let exports: [UInt8] = [2] + name("startup") + [0,0] + name("mixer_guest_capability_ready_v1") + [0,1]
        let code: [UInt8] = invalidUncalled ? [3,2,0,0x0b,2,0,0x0b,3,0,0xff,0x0b] : [2,2,0,0x0b,2,0,0x0b]
        return Data([0,97,115,109,1,0,0,0] + section(1,[1,0x60,0,0]) + section(3,invalidUncalled ? [3,0,0,0] : [2,0,0])
            + section(5,[1,0,memoryPages]) + section(7,exports) + section(10,code))
    }
}
enum New {
    static func wasm(invalidUncalled: Bool = false, memoryPages: UInt8 = 0) -> Data {
        func name(_ value: String) -> [UInt8] { [UInt8(value.utf8.count)] + Array(value.utf8) }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id, UInt8(bytes.count)] + bytes }
        let exports: [UInt8] = [2] + name("startup") + [0,0] + name("mixer_guest_capability_ready_v1") + [0,1]
        let code: [UInt8] = invalidUncalled ? [3,2,0,0x0b,2,0,0x0b,3,0,0xff,0x0b] : [2,2,0,0x0b,2,0,0x0b]
        var bytes: [UInt8] = [0,97,115,109,1,0,0,0]
        bytes += section(1,[1,0x60,0,0])
        bytes += section(3,invalidUncalled ? [3,0,0,0] : [2,0,0])
        bytes += section(5,[1,0,memoryPages])
        bytes += section(7,exports)
        bytes += section(10,code)
        return Data(bytes)
    }
}
for invalid in [false,true] { for n in UInt16(0)...255 { precondition(Old.wasm(invalidUncalled:invalid,memoryPages:UInt8(n)) == New.wasm(invalidUncalled:invalid,memoryPages:UInt8(n))) } }
print("PASS 512 exact fixture byte comparisons")
