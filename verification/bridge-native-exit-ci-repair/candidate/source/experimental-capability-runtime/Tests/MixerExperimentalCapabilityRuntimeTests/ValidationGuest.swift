import Foundation

/// Original small module encoder, reusing this lane's own LEB/section helpers.
enum ValidationGuest {
    struct Import { let module: String; let name: String; let parameters: [UInt8]; let result: UInt8? }
    static func signature(_ parameters: [UInt8], _ result: UInt8?) -> [UInt8] { GuestProgram.sig(parameters, result) }
    static func build(startup: String = "boot", startupParameters: [UInt8] = [], wakeResult: UInt8? = nil,
                      memoryCount: Int = 1, memoryMinimum: UInt32 = 0, memoryMaximum: UInt32? = 0, memoryFlags: UInt8? = nil,
                      imports: [Import] = [], importedStartup: Bool = false, importedWake: Bool = false, omitWake: Bool = false,
                      boot: [UInt8] = [0x0b], wake: [UInt8] = [0x0b], run: [UInt8] = [0x41,0,0x0b],
                      extraBodies: [[UInt8]] = [], start: Bool = false, badData: Bool = false, badElement: Bool = false,
                      arguments: Data? = nil, tableMinimum: UInt32? = nil, initialBootElement: Bool = false) -> Data {
        let u = GuestProgram.u, text = GuestProgram.text, section = GuestProgram.section
        let types = [signature(startupParameters,nil), signature([],wakeResult), signature([],0x7f)] + imports.map { signature($0.parameters,$0.result) }
        var bytes = [UInt8](arrayLiteral: 0,97,115,109,1,0,0,0)
        bytes += section(1,u(UInt32(types.count))+types.flatMap{$0})
        if !imports.isEmpty {
            var data = u(UInt32(imports.count))
            for (index,item) in imports.enumerated() { data += text(item.module)+text(item.name)+[0]+u(UInt32(index+3)) }
            bytes += section(2,data)
        }
        bytes += section(3,u(UInt32(3+extraBodies.count))+[0,1,2]+Array(repeating: UInt8(0),count:extraBodies.count))
        if let minimum = tableMinimum { bytes += section(4,[1,0x70,1]+u(minimum)+u(minimum)) }
        else if badElement { bytes += section(4,[1,0x70,1,0,0]) }
        if memoryCount > 0 {
            var memory = u(UInt32(memoryCount))
            for _ in 0..<memoryCount { memory += [memoryFlags ?? (memoryMaximum == nil ? 0 : 1)]+u(memoryMinimum)+(memoryMaximum.map(u) ?? []) }
            bytes += section(5,memory)
        }
        var exports = u(omitWake ? 2 : 3)
        exports += text(startup)+[0]+u(importedStartup ? 0 : UInt32(imports.count))
        if !omitWake { exports += text("mixer_guest_capability_ready_v1")+[0]+u(importedWake ? 0 : UInt32(imports.count+1)) }
        exports += text("run")+[0]+u(UInt32(imports.count+2))
        bytes += section(7,exports)
        if start { bytes += section(8,u(UInt32(imports.count))) }
        if badElement || initialBootElement { bytes += section(9,[1,0,0x41,0,0x0b,1]+u(UInt32(imports.count))) }
        let bodies = [boot,wake,run]+extraBodies
        var code = u(UInt32(bodies.count))
        for body in bodies { code += u(UInt32(body.count+1))+[0]+body }
        bytes += section(10,code)
        if badData { bytes += section(11,[1,0,0x41,0,0x0b,1,7]) }
        else if let arguments {
            var data = [UInt8](arrayLiteral: 1,0)
            data += GuestProgram.i(1024)
            data += [0x0b]
            data += u(UInt32(arguments.count))
            data += arguments
            bytes += section(11,data)
        }
        return Data(bytes)
    }
    static func padded(_ module: Data, count: Int) -> Data {
        let n = count-module.count-7 // tag1 + four-byte section LEB + one-byte name length/name
        precondition(n > 0)
        return module+Data(GuestProgram.section(0,[1,0x70]+Array(repeating: UInt8(0),count:n)))
    }
}
