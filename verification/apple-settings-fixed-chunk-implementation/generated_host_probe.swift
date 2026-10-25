import Foundation
import CoreFoundation
import CryptoKit
private final class SettingsTelemetry: @unchecked Sendable {
    static let shared = SettingsTelemetry()
    private let chunkBytes = 4992
    let fixedCase = "public-settings-full-keyboard-access"
    private var generation = ""
    private var sequence = 0
    private var transport = DiagnosticTransportState()
    private let firstFailureDiagnostic = SettingsFirstFailureDiagnostic()
    private let lock = NSRecursiveLock()
    private final class Box: @unchecked Sendable { var data: Data?; var status: Int?; var error: Error? }
    enum Failure: Error { case budget, bridge, upload, setup(String) }
    private var now: Double { ProcessInfo.processInfo.systemUptime }
    static var hostRecords: [[String:Any]] = []
    static var hostReply: [String:Any] = [:]
    private func post(_ record:[String:Any]) throws -> [String:Any] {
        let body = try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes])
        guard body.count <= 8192 else { throw Failure.upload }
        Self.hostRecords.append(record)
        if record["kind"] as? String == "start" { return Self.hostReply }
        if record["kind"] as? String == "observe" {
            let files = record["files"] as! [String:Any]
            return ["pending": ["ax","png"].filter { files[$0] != nil }.map { "settings-" + String(format:"%04d",record["sequence"] as! Int) + "-" + $0 }]
        }
        return ["accepted":true]
    }
    func start() throws {
        lock.lock(); defer { lock.unlock() }
        let initial = now; transport.deadline = initial + 29.0
        let result = try post(["kind": "start", "case": fixedCase, "uptime": initial, "chunkBytes": chunkBytes])
        guard let format = result["chunkBytes"] as? NSNumber,
              CFGetTypeID(format) != CFBooleanGetTypeID(),
              ["s", "i", "l", "q", "S", "I", "L", "Q"].contains(String(cString: format.objCType)),
              format.intValue == chunkBytes,
              let token = result["generation"] as? String, let remaining = result["remainingSessionSeconds"] as? Double else { throw Failure.bridge }
        generation = token; transport.deadline = min(transport.deadline, now + remaining)
    }
    private func send(_ fields: [String: Any]) throws -> [String: Any] {
        sequence += 1
        var value = fields
        value["case"] = fixedCase; value["generation"] = generation; value["sequence"] = sequence; value["uptime"] = now
        return try post(value)
    }
    func mark(_ stage: String, _ detail: [String: Any] = [:]) throws {
        lock.lock(); defer { lock.unlock() }
        _ = try send(["kind": "mark", "stage": stage, "detail": detail])
        print("MIXER_SETTINGS_DIAGNOSTIC " + stage)
    }
    func bestEffortMark(_ stage: String) { do { try mark(stage) } catch { print("MIXER_SETTINGS_DIAGNOSTIC_UNAVAILABLE " + stage + " " + String(describing: error)) } }
    func observe(_ stage: String, routeIndex: Int, attempt: Int, snapshot: [String: Any], started: Double, finished: Double, ax: Data?, png: Data?, routeWitness: [String: Any]? = nil, switchWitness: [String: Any]? = nil) throws -> Int {
        lock.lock(); defer { lock.unlock() }
        var files: [String: Any] = [:]; var payloads: [String: Data] = [:]
        for (form, payload, limit) in [("ax", ax, 200_000), ("png", png, 2_000_000)] {
            if let payload {
                guard payload.count > 0, payload.count <= limit else { throw Failure.upload }
                let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
                files[form] = ["bytes": payload.count, "sha256": digest]; payloads[form] = payload
            }
        }
        var record: [String: Any] = ["kind": "observe", "stage": stage, "routeIndex": routeIndex, "attempt": attempt,
                               "captureStartedUptime": started, "captureFinishedUptime": finished, "snapshot": snapshot, "files": files]
        if let routeWitness { record["routeWitness"] = routeWitness }
        if let switchWitness { record["switchWitness"] = switchWitness }
        let eventSequence = sequence + 1
        let result = try send(record)
        guard let slots = result["pending"] as? [String] else { throw Failure.bridge }
        for slot in slots {
            let form = slot.hasSuffix("-ax") ? "ax" : "png"
            guard let payload = payloads[form], let descriptor = files[form] as? [String: Any] else { throw Failure.upload }
            let count = (payload.count + chunkBytes - 1) / chunkBytes
            for index in 0..<count {
                let chunk = payload.subdata(in: index * chunkBytes..<min(payload.count, (index + 1) * chunkBytes))
                _ = try send(["kind": "chunk", "slot": slot, "index": index, "count": count, "bytes": payload.count,
                              "sha256": descriptor["sha256"]!, "data": chunk.base64EncodedString()])
            }
        }
        return eventSequence
    }
}

extension SettingsTelemetry {
    var hostSessionAccepted: Bool { !generation.isEmpty }
}
func expect(_ value: @autoclosure () -> Bool, _ reason: String) {
    if !value() { fatalError(reason) }
}
func didThrow(_ call: () throws -> Void) -> Bool { do { try call(); return false } catch { return true } }
var rows: [[String:Any]]=[]
let uptimes:[Double]=[0,-0.0,Double.leastNonzeroMagnitude,Double.leastNormalMagnitude,Double.greatestFiniteMagnitude,943842.1664629584,1.0.nextDown,1.0.nextUp]
for count in [1,2,3,4991,4992] {
    for slashHeavy in [false,true] {
        let payload=slashHeavy ? Data(repeating:255,count:count) : Data((0..<count).map { UInt8($0 % 256) })
        for uptime in uptimes {
            let record:[String:Any]=["kind":"chunk","case":"public-settings-full-keyboard-access","generation":"ffffffff-ffff-ffff-ffff-ffffffffffff","sequence":2500,"uptime":uptime,"slot":"settings-2500-png","index":400,"count":401,"bytes":2000000,"sha256":String(repeating:"f",count:64),"data":payload.base64EncodedString()]
            let data=try JSONSerialization.data(withJSONObject:["settingsDiagnostic":record],options:[.sortedKeys,.withoutEscapingSlashes])
            expect(data.count<=8192,"actual Foundation body guard")
            let result=try JSONSerialization.jsonObject(with:data) as! [String:Any]
            let decoded=result["settingsDiagnostic"] as! [String:Any]
            expect(Data(base64Encoded:decoded["data"] as! String)==payload,"Foundation byte roundtrip")
            expect(!String(decoding:data,as:UTF8.self).contains("\\/"),"JSON slash escaped")
            rows.append(["decodedBytes":count,"slashHeavy":slashHeavy,"uptime":String(uptime),"bodyBytes":data.count,"base64Bytes":payload.base64EncodedString().utf8.count])
        }
    }
}
// Exact start handshake is run through the actual changed start method.
var echoes:[[String:Any]]=[]
let echoValues:[Any?]=[nil,true,false,"4992",3072,4993,NSNumber(value:4992.0),NSNull(),[4992],4992]
for echo in echoValues {
    var reply:[String:Any]=["generation":"ffffffff-ffff-ffff-ffff-ffffffffffff","remainingSessionSeconds":29.0]
    if let echo { reply["chunkBytes"]=echo }
    SettingsTelemetry.hostReply=reply;SettingsTelemetry.hostRecords=[]
    let client=SettingsTelemetry()
    let failed=didThrow { try client.start() }
    let expected=(echo as? NSNumber).map { CFGetTypeID($0) != CFBooleanGetTypeID() && ["s","i","l","q","S","I","L","Q"].contains(String(cString:$0.objCType)) && $0.intValue==4992 } ?? false
    expect(client.hostSessionAccepted==expected && failed != expected,"format echo acceptance")
    expect(SettingsTelemetry.hostRecords.count==1,"no fallback or retry")
    expect(SettingsTelemetry.hostRecords[0]["chunkBytes"] as? Int==4992,"mandatory exact start format")
    echoes.append(["value":String(describing:echo),"sessionAccepted":client.hostSessionAccepted])
}
var rawEchoRows:[[String:Any]]=[]
for token in ["4992","4992.0","4.992e3","true","\"4992\"","3072","null"] {
    let reply=try JSONSerialization.jsonObject(with:Data(("{\"chunkBytes\":"+token+",\"generation\":\"ffffffff-ffff-ffff-ffff-ffffffffffff\",\"remainingSessionSeconds\":29}").utf8)) as! [String:Any]
    SettingsTelemetry.hostReply=reply;let client=SettingsTelemetry();let failed=didThrow { try client.start() }
    let number=reply["chunkBytes"] as? NSNumber
    rawEchoRows.append(["token":token,"objCType":number.map { String(cString:$0.objCType) } ?? "none","sessionAccepted":!failed])
    expect((!failed)==(token=="4992"),"wrong JSON echo type accepted: "+token)
}
var packing:[[String:Any]]=[]
for size in [1,4991,4992,4993,9984,200000,2000000] {
    SettingsTelemetry.hostRecords=[];SettingsTelemetry.hostReply=["generation":"ffffffff-ffff-ffff-ffff-ffffffffffff","remainingSessionSeconds":29.0,"chunkBytes":4992]
    let client=SettingsTelemetry();try client.start()
    let payload=Data((0..<size).map { UInt8($0 % 256) })
    _=try client.observe("before-switch",routeIndex:3,attempt:0,snapshot:[:],started:0,finished:0,ax:nil,png:payload)
    let records=SettingsTelemetry.hostRecords.filter { $0["kind"] as? String=="chunk" }
    expect(records.count==(size+4991)/4992,"actual client count")
    var assembled=Data()
    for (index,record) in records.enumerated() {
        expect(record["index"] as? Int==index,"actual client chunk order")
        let bytes=Data(base64Encoded:record["data"] as! String)!
        expect(bytes.count==min(4992,size-index*4992),"actual client exact decoded length")
        expect((record["data"] as! String).utf8.count<=6656,"client base64 maximum")
        assembled.append(bytes)
    }
    expect(assembled==payload,"actual client payload identity")
    packing.append(["bytes":size,"chunks":records.count,"lastBytes":size-4992*(records.count-1)])
}
SettingsTelemetry.hostRecords=[];SettingsTelemetry.hostReply=["generation":"x","remainingSessionSeconds":29.0,"chunkBytes":4992]
private let guarded=SettingsTelemetry();try guarded.start()
let tooLarge=["padding":String(repeating:"/",count:8192)]
expect(didThrow { _=try guarded.observe("before-switch",routeIndex:3,attempt:0,snapshot:tooLarge,started:0,finished:0,ax:nil,png:nil) },"actual 8192 body guard")
expect(SettingsTelemetry.hostRecords.count==1,"oversized body was admitted")
// Original transport is compiled byte-identically and exercised directly.
var transport=DiagnosticTransportState();transport.deadline=29
let allowance=try transport.begin(now:0);expect(allowance==2,"two-second ceiling")
let clipped=try transport.begin(now:28.99);expect(clipped<0.011,"absolute deadline clips request")
expect(didThrow { _=try transport.begin(now:29) },"29 second deadline")
var capped=DiagnosticTransportState();capped.deadline=29;capped.requests=2500
expect(didThrow { _=try capped.begin(now:0) },"2500 request cap")
for data in [Data(repeating:32,count:8193),Data("[]".utf8)] {
    var state=DiagnosticTransportState();state.deadline=29
    expect(didThrow { _=try state.response(status:200,data:data,networkError:nil) },"bounded invalid response")
    expect(state.firstFailure != nil,"response first failure latched")
    expect(didThrow { _=try state.begin(now:0) },"sticky first failure")
}
var sticky=DiagnosticTransportState();let first=sticky.latch(.network("first"));_ = sticky.latch(.responseInvalid)
expect(sticky.firstFailure==first,"first failure replaced")
let output:[String:Any]=["passed":true,"serializationRows":rows,"echoRows":echoes,"rawJSONEchoRows":rawEchoRows,"actualClientPacking":packing,"actualBodyGuard":true,"originalTransportLimitsAndStickyFailure":true,"scope":"host Foundation; post is a generated in-process stub; no HTTP/native execution"]
FileHandle.standardOutput.write(try JSONSerialization.data(withJSONObject:output,options:[.prettyPrinted,.sortedKeys,.withoutEscapingSlashes]))
FileHandle.standardOutput.write(Data([10]))
