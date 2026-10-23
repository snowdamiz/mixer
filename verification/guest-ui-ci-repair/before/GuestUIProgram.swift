import Foundation

/// Independently authored narrow Wasm program. It checks every event byte and
/// checks the exact successful committed storage completion before publishing
/// Saved sample. It uses no engine fixture, compiler, generated guest or parser.
enum GuestUIProgram {
    enum Mode: Equatable { case normal, invalidStartupHeader, overlappingRanges, outsideMemory, invalidEventDocument, nonzeroEvent, invalidWakeDocument, changedWakeBuffer, regressedWake, sameRevisionWake, unconsumed, confirmationWindow }
    static let event = Data(#"{"actionID":"sample.save","event":"activate","nodeID":"save","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#.utf8)
    static func document(revision: UInt64, label: String = "Ready") -> Data {
        Data("{\"schemaVersion\":1,\"revision\":\(revision),\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"\(label)\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}],\"actions\":[]}}".utf8)
    }
    static func header(document: UInt32, length: UInt32, event: UInt32 = 4096, magic: UInt32 = 0x3155494d) -> Data {
        var bytes: [UInt8] = []
        for value in [magic, 32, document, length, event, 4096, 0, 0] {
            for shift in stride(from: 0, to: 32, by: 8) { bytes.append(UInt8(truncatingIfNeeded: value >> shift)) }
        }
        return Data(bytes)
    }
    static func build(_ mode: Mode = .normal, initialRevision: UInt64 = 1) -> Data {
        let u = GuestProgram.u, i = GuestProgram.i, text = GuestProgram.text, section = GuestProgram.section
        let initial = document(revision: initialRevision)
        let expectedEvent = Data(String(decoding: event, as: UTF8.self).replacingOccurrences(of: "\"revision\":1", with: "\"revision\":\(initialRevision)").utf8)
        let nextRevision: UInt64 = mode == .regressedWake ? 1 : mode == .sameRevisionWake ? initialRevision : initialRevision + 1
        let saved = document(revision: nextRevision, label: "Saved sample")
        let put = Data(#"{"namespace":"entries","key":"binary","valueBase64":"AAH+/w=="}"#.utf8)
        let committed = Data(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":{"kind":"success","value":{"committed":true}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#.utf8)
        func store(_ address: Int32, _ value: Int32) -> [UInt8] { i(address) + i(value) + [0x36, 0, 0] }
        func checkBytes(_ address: Int32, _ bytes: Data) -> [UInt8] {
            var code: [UInt8] = []
            for (index, byte) in bytes.enumerated() {
                code += i(address + Int32(index)) + [0x2d, 0, 0] + i(Int32(byte)) + [0x47, 0x04, 0x40, 0x00, 0x0b]
            }
            return code
        }
        var eventBody = [UInt8](arrayLiteral: 0x20, 0) + i(Int32(expectedEvent.count)) + [0x47,0x04,0x40,0x00,0x0b]
        eventBody += checkBytes(4096, expectedEvent)
        eventBody += i(9000) + i(Int32(put.count)) + i(128) + [0x10, 0, 0x1a]
        if mode == .invalidEventDocument { eventBody += store(15, 3000) + store(19, 2) }
        eventBody += i(mode == .nonzeroEvent ? 1 : 0) + [0x0b]
        var ready = i(128) + [0x29,0,0] + i(10000) + i(2048) + i(160) + [0x10,1,0x45,0x04,0x40]
        // Consume failure without claiming that storage committed. Saved sample
        // is published only when both the byte length and entire packet match.
        ready += i(160) + [0x28,0,0] + i(Int32(committed.count)) + [0x46,0x04,0x40]
        ready += checkBytes(10000, committed)
        switch mode {
        case .invalidWakeDocument:
            // Enqueue a second write during the invalid turn. The bridge must
            // harvest its invalid UI before taking/admitting this new request.
            ready += i(9000) + i(Int32(put.count)) + i(128) + [0x10, 0, 0x1a]
            ready += store(15, 3000) + store(19, 2)
        case .changedWakeBuffer: ready += store(23, 16384)
        default: ready += store(15, 2048) + store(19, Int32(saved.count))
        }
        // This overwrite detects any wake incorrectly interleaved between the
        // host event copy and event export's byte checks.
        ready += i(4096) + i(90) + [0x3a,0,0,0x0b,0x0b,0x0b]
        if mode == .unconsumed { ready = [0x0b] }
        var startup = i(7) + [0x0b]
        if mode == .confirmationWindow {
            let enqueue = i(9000) + i(Int32(put.count)) + i(128) + [0x10,0,0x1a]
            startup = enqueue + startup
            // Consume even a pre-enable unavailable completion and enqueue the
            // next request. This leaves concrete work waiting in the window
            // between actual native enable and durable host confirmation.
            ready = i(128) + [0x29,0,0] + i(10000) + i(2048) + i(160) + [0x10,1,0x45,0x04,0x40]
            ready += enqueue + [0x0b,0x0b]
        }
        let types = [GuestProgram.sig([0x7f,0x7f,0x7f],0x7f), GuestProgram.sig([0x7e,0x7f,0x7f,0x7f],0x7f), GuestProgram.sig([],0x7f), GuestProgram.sig([0x7f],0x7f), GuestProgram.sig([],nil)]
        var imports = u(2)
        imports += text("mixer.capability.v1") + text("storage_put") + [0,0]
        imports += text("mixer.capability.v1") + text("poll") + [0,1]
        var exports = u(3)
        for (name, index) in [("mixer_guest_ui_start_v1",2),("mixer_guest_ui_event_v1",3),("mixer_guest_capability_ready_v1",4)] { exports += text(name) + [0] + u(UInt32(index)) }
        let bodies = [startup, eventBody, ready]
        var code = u(UInt32(bodies.count))
        for body in bodies { code += u(UInt32(body.count + 1)) + [0] + body }
        let pointer: UInt32 = mode == .overlappingRanges ? 7 : mode == .outsideMemory ? 65530 : 1024
        let control = header(document: pointer, length: UInt32(initial.count), magic: mode == .invalidStartupHeader ? 0 : 0x3155494d)
        var data = u(5)
        for (address, bytes) in [(Int32(7),control),(1024,initial),(2048,saved),(3000,Data("[]".utf8)),(9000,put)] {
            data += [0] + i(address) + [0x0b] + u(UInt32(bytes.count)) + bytes
        }
        var module: [UInt8] = [0,97,115,109,1,0,0,0]
        module += section(1,u(UInt32(types.count)) + types.flatMap { $0 })
        module += section(2,imports)
        module += section(3,[3,2,3,4])
        module += section(5,[1,1,1,64])
        module += section(7,exports)
        module += section(10,code)
        module += section(11,data)
        return Data(module)
    }
}
