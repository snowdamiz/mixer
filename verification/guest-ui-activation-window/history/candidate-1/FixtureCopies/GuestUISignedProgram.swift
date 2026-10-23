import Foundation

/// Original core-Wasm binary for signed activation tests, independent of VM
/// fixture builders. One native button submits an actual app-private put. A
/// distinct Saving frame precedes Saved, which requires the exact committed
/// success packet. This is a narrow test program, not a Swift guest compiler.
enum GuestUISignedProgram {
    enum Mode { case valid, invalidHeader, invalidEventDocument, invalidWakeDocument, missingEvent }
    static let event = Data(#"{"actionID":"sample.save","event":"activate","nodeID":"save","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#.utf8)
    static func document(_ revision: Int, _ status: String) -> Data {
        Data("{\"schemaVersion\":1,\"revision\":\(revision),\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"\(status)\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}],\"actions\":[]}}".utf8)
    }
    static func build(_ mode: Mode = .valid) -> Data {
        func u(_ value: Int) -> [UInt8] {
            var n = value, out: [UInt8] = []
            repeat { let b = UInt8(n & 127); n >>= 7; out.append(b | (n == 0 ? 0 : 128)) } while n != 0
            return out
        }
        func i(_ value: Int) -> [UInt8] {
            var n = value, out: [UInt8] = [0x41]
            while true {
                let b = UInt8(n & 127); n >>= 7
                let done = (n == 0 && b & 64 == 0) || (n == -1 && b & 64 != 0)
                out.append(b | (done ? 0 : 128)); if done { return out }
            }
        }
        func text(_ value: String) -> [UInt8] { u(value.utf8.count) + value.utf8 }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] { [id] + u(bytes.count) + bytes }
        func store(_ address: Int, _ value: Int) -> [UInt8] { i(address) + i(value) + [0x36,0,0] }
        func check(_ address: Int, _ bytes: Data) -> [UInt8] {
            var out: [UInt8] = []
            for (n,b) in bytes.enumerated() { out += i(address+n) + [0x2d,0,0] + i(Int(b)) + [0x47,0x04,0x40,0x00,0x0b] }
            return out
        }
        let ready = document(1,"Ready"), saving = document(2,"Saving sample"), saved = document(3,"Saved sample")
        let denied = document(3,"Save unavailable")
        let request = Data(#"{"namespace":"material_test","key":"binary","valueBase64":"AAH+/w=="}"#.utf8)
        let committed = Data(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":{"kind":"success","value":{"committed":true}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#.utf8)
        var eventBody = [UInt8](arrayLiteral:0x20,0) + i(event.count) + [0x47,0x04,0x40,0x00,0x0b]
        eventBody += check(4096,event)
        eventBody += i(9000) + i(request.count) + i(128) + [0x10,0,0x1a]
        eventBody += store(15,mode == .invalidEventDocument ? 8192 : 2048)
        eventBody += store(19,mode == .invalidEventDocument ? 2 : saving.count)
        eventBody += i(0) + [0x0b]
        var wake = i(128) + [0x29,0,0] + i(10000) + i(2048) + i(160) + [0x10,1,0x45,0x04,0x40]
        wake += i(160) + [0x28,0,0] + i(committed.count) + [0x46,0x04,0x40]
        wake += check(10000,committed)
        wake += store(15,mode == .invalidWakeDocument ? 8192 : 3000)
        wake += store(19,mode == .invalidWakeDocument ? 2 : saved.count)
        wake += [0x05] + store(15,3500) + store(19,denied.count) + [0x0b,0x0b,0x0b]
        var types: [UInt8] = [5]
        types += [0x60,3,0x7f,0x7f,0x7f,1,0x7f]
        types += [0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f]
        types += [0x60,0,1,0x7f,0x60,1,0x7f,1,0x7f,0x60,0,0]
        var imports: [UInt8] = [2]
        imports += text("mixer.capability.v1") + text("storage_put") + [0,0]
        imports += text("mixer.capability.v1") + text("poll") + [0,1]
        var exports: [UInt8] = [mode == .missingEvent ? 2 : 3]
        exports += text("mixer_guest_ui_start_v1") + [0,2]
        if mode != .missingEvent { exports += text("mixer_guest_ui_event_v1") + [0,3] }
        exports += text("mixer_guest_capability_ready_v1") + [0,4]
        var code: [UInt8] = [3]
        for body in [i(7)+[0x0b],eventBody,wake] { code += u(body.count+1) + [0] + body }
        var header: [UInt8] = []
        for v: UInt32 in [mode == .invalidHeader ? 0 : 0x3155494d,32,1024,UInt32(ready.count),4096,4096,0,0] {
            for shift in stride(from:0,to:32,by:8) { header.append(UInt8(truncatingIfNeeded:v >> shift)) }
        }
        var data: [UInt8] = [7]
        for (offset,bytes) in [(7,Data(header)),(1024,ready),(2048,saving),(3000,saved),(3500,denied),(8192,Data("[]".utf8)),(9000,request)] {
            data += [0] + i(offset) + [0x0b] + u(bytes.count) + bytes
        }
        var module: [UInt8] = [0,97,115,109,1,0,0,0]
        module += section(1,types); module += section(2,imports)
        module += section(3,[3,2,3,4]); module += section(5,[1,1,1,1])
        module += section(7,exports); module += section(10,code); module += section(11,data)
        return Data(module)
    }
}
