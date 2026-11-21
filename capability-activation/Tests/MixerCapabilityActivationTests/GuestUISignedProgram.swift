import Foundation
import MixerCapabilities

/// Original core-Wasm binary for signed activation tests, independent of VM
/// fixture builders. One native button submits app-private storage work. The
/// output frames depend on the exact completion packets the guest observes.
enum GuestUISignedProgram {
    enum Mode {
        case valid, invalidHeader, invalidEventDocument, invalidWakeDocument, missingEvent, localizedChecklist
        case commitFacts, invalidCommitFacts, readyCommitFacts

        var readsFacts: Bool { self == .commitFacts || self == .invalidCommitFacts || self == .readyCommitFacts }
    }
    static let event = Data(#"{"actionID":"sample.save","event":"activate","nodeID":"save","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#.utf8)
    static func document(_ revision: Int, _ status: String) -> Data {
        Data("{\"schemaVersion\":1,\"revision\":\(revision),\"root\":{\"id\":\"root\",\"kind\":\"vStack\",\"properties\":{},\"children\":[{\"id\":\"status\",\"kind\":\"text\",\"properties\":{\"text\":\"\(status)\"},\"children\":[],\"actions\":[]},{\"id\":\"save\",\"kind\":\"button\",\"properties\":{\"label\":\"Save sample\"},\"children\":[],\"actions\":[{\"id\":\"sample.save\",\"event\":\"activate\"}]}],\"actions\":[]}}".utf8)
    }
    static func build(_ mode: Mode = .valid, storageNamespace: String = "material_test",
                      expectedDenial: Data? = nil) -> Data {
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
        func text(_ value: String) -> [UInt8] {
            var out: [UInt8] = u(value.utf8.count)
            out += value.utf8
            return out
        }
        func section(_ id: UInt8, _ bytes: [UInt8]) -> [UInt8] {
            var out: [UInt8] = [id]
            out += u(bytes.count)
            out += bytes
            return out
        }
        func store(_ address: Int, _ value: Int) -> [UInt8] {
            var out: [UInt8] = i(address)
            out += i(value)
            out += [0x36,0,0]
            return out
        }
        func check(_ address: Int, _ bytes: Data) -> [UInt8] {
            var out: [UInt8] = []
            for (n,b) in bytes.enumerated() {
                out += i(address+n)
                out += [0x2d,0,0]
                out += i(Int(b))
                out += [0x47,0x04,0x40,0x00,0x0b]
            }
            return out
        }
        func enqueue(_ offset: Int, _ length: Int, token: Int) -> [UInt8] {
            i(offset) + i(length) + i(token) + [0x10, 0, 0x1a]
        }
        func poll(_ token: Int) -> [UInt8] {
            i(token) + [0x29, 0, 0] + i(10000) + i(2048) + i(160) + [0x10, 1]
        }
        func checkCompletion(_ bytes: Data) -> [UInt8] {
            i(160) + [0x28, 0, 0] + i(bytes.count) + [0x47, 0x04, 0x40, 0x00, 0x0b] + check(10000, bytes)
        }
        func frame(_ revision: Int, _ status: String, localizedStatus: String) -> Data {
            guard mode == .localizedChecklist else { return document(revision, status) }
            return Data("""
                {"schemaVersion":1,"revision":\(revision),"root":{"id":"fieldlog-task","kind":"vStack","properties":{},"actions":[],"children":[
                  {"id":"task","kind":"text","properties":{"text":"فحص المضخة 07"},"children":[],"actions":[]},
                  {"id":"status","kind":"text","properties":{"text":"\(localizedStatus)"},"children":[],"actions":[]},
                  {"id":"toggle","kind":"button","properties":{"label":"وضع علامة مكتملة"},"children":[],"actions":[{"id":"task.toggle","event":"activate"}]}
                ]}}
                """.utf8)
        }
        let ready = frame(1, "Ready", localizedStatus: "الفحص قيد التنفيذ")
        let saving = frame(2, "Saving sample", localizedStatus: "جارٍ الحفظ")
        let saved = frame(3, "Saved sample", localizedStatus: "اكتمل الفحص")
        let denied = frame(3, "Save unavailable", localizedStatus: "تعذر الحفظ")
        let checkedFacts = document(4, "Unattributed facts denied")
        let event = mode == .localizedChecklist
            ? Data(#"{"actionID":"task.toggle","event":"activate","nodeID":"toggle","revision":1,"schemaVersion":1,"sequence":1,"value":null}"#.utf8)
            : Self.event
        let facts = Data(#"{"namespace":"material_test","key":"facts"}"#.utf8)
        let request = if mode == .readyCommitFacts { Data(#"{"namespace":"material_test","key":"trigger"}"#.utf8) }
            else if mode.readsFacts { facts }
            else { Data(#"{"namespace":"\#(storageNamespace)","key":"binary","valueBase64":"AAH+/w=="}"#.utf8) }
        let committed = mode.readsFacts
            ? try! GuestCapabilityTransportCodecV1.encodeCompletion(.success(.get(.init(found: true, valueBase64: "AQ=="))), operation: .storageGet)
            : Data(#"{"abi":1,"capability":"storage.keyValue.v1","operation":"put","outcome":{"kind":"success","value":{"committed":true}},"schemaHash":"4a311222c978ddd0982e8dfbcf3d4864b856a80bcc1efb3b725adede7f8e22fd"}"#.utf8)
        let deniedFacts = try! GuestCapabilityTransportCodecV1.encodeCompletion(.failure(.permissionDenied), operation: .storageGet)
        let expected = expectedDenial ?? committed
        var eventBody: [UInt8] = [0x20,0]
        eventBody += i(event.count)
        eventBody += [0x47,0x04,0x40,0x00,0x0b]
        eventBody += check(4096,event)
        eventBody += enqueue(9000, request.count, token: 128)
        if mode == .commitFacts { eventBody += enqueue(9200, facts.count, token: 136) }
        let invalidEvent = mode == .invalidEventDocument || mode == .invalidCommitFacts
        eventBody += store(15,invalidEvent ? 8192 : 2048)
        eventBody += store(19,invalidEvent ? 2 : saving.count)
        eventBody += i(0)
        eventBody += [0x0b]
        var wake = poll(128)
        wake += [0x45,0x04,0x40]
        wake += i(160)
        wake += [0x28,0,0]
        wake += i(expected.count)
        wake += [0x46,0x04,0x40]
        wake += check(10000,expected)
        if mode == .readyCommitFacts { wake += enqueue(9200, facts.count, token: 136) }
        if expectedDenial != nil {
            wake += store(15,3500)
            wake += store(19,denied.count)
        } else {
            wake += store(15,mode == .invalidWakeDocument ? 8192 : 3000)
            wake += store(19,mode == .invalidWakeDocument ? 2 : saved.count)
        }
        wake += [0x05]
        if expectedDenial != nil {
            wake += [0x00] // A different completion cannot satisfy the scoped denial control.
        } else {
            wake += store(15,3500)
            wake += store(19,denied.count)
        }
        wake += [0x0b,0x0b]
        if mode == .commitFacts || mode == .readyCommitFacts {
            // Wait for the success frame, then verify the second read's denial.
            wake += i(15) + [0x28,0,0] + i(3000) + [0x46,0x04,0x40]
            wake += poll(136) + [0x45,0x04,0x40]
            wake += checkCompletion(deniedFacts)
            wake += store(15, 8550) + store(19, checkedFacts.count)
            wake += [0x0b,0x0b]
        }
        wake += [0x0b]
        var types: [UInt8] = [5]
        types += [0x60,3,0x7f,0x7f,0x7f,1,0x7f]
        types += [0x60,4,0x7e,0x7f,0x7f,0x7f,1,0x7f]
        types += [0x60,0,1,0x7f,0x60,1,0x7f,1,0x7f,0x60,0,0]
        var imports: [UInt8] = [2]
        imports += text("mixer.capability.v1")
        imports += text(mode.readsFacts ? "storage_get" : "storage_put")
        imports += [0,0]
        imports += text("mixer.capability.v1")
        imports += text("poll")
        imports += [0,1]
        var exports: [UInt8] = [mode == .missingEvent ? 2 : 3]
        exports += text("mixer_guest_ui_start_v1")
        exports += [0,2]
        if mode != .missingEvent {
            exports += text("mixer_guest_ui_event_v1")
            exports += [0,3]
        }
        exports += text("mixer_guest_capability_ready_v1")
        exports += [0,4]
        var code: [UInt8] = [3]
        var startup: [UInt8] = []
        if mode.readsFacts {
            let unavailable = try! GuestCapabilityTransportCodecV1.encodeCompletion(.failure(.unavailable), operation: .storageGet)
            startup += enqueue(9200, facts.count, token: 144)
            startup += poll(144) + [0x04, 0x40, 0x00, 0x0b]
            startup += checkCompletion(unavailable)
        }
        startup += i(7) + [0x0b]
        for body in [startup,eventBody,wake] {
            code += u(body.count+1)
            code += [0]
            code += body
        }
        var header: [UInt8] = []
        for v: UInt32 in [mode == .invalidHeader ? 0 : 0x3155494d,32,1024,UInt32(ready.count),4096,4096,0,0] {
            for shift in stride(from:0,to:32,by:8) { header.append(UInt8(truncatingIfNeeded:v >> shift)) }
        }
        var segments = [(7,Data(header)),(1024,ready),(2048,saving),(3000,saved),(3500,denied),(8192,Data("[]".utf8)),(9000,request)]
        if mode.readsFacts { segments += [(8550,checkedFacts),(9200,facts)] }
        var data = u(segments.count)
        for (offset,bytes) in segments {
            data += [0]
            data += i(offset)
            data += [0x0b]
            data += u(bytes.count)
            data += bytes
        }
        var module: [UInt8] = [0,97,115,109,1,0,0,0]
        module += section(1,types); module += section(2,imports)
        module += section(3,[3,2,3,4]); module += section(5,[1,1,1,1])
        module += section(7,exports); module += section(10,code); module += section(11,data)
        return Data(module)
    }
}
