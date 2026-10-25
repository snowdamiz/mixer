import Foundation
func body(_ n: Int, chunkSize: Int, slashless: Bool, uptime: Double, last: Bool = false) throws -> Data {
    let payload = Data(repeating: 255, count: n)
    let count = (2_000_000 + chunkSize - 1) / chunkSize
    let record: [String: Any] = ["kind":"chunk", "case":"public-settings-full-keyboard-access", "generation":"ffffffff-ffff-ffff-ffff-ffffffffffff", "sequence":2500, "uptime":uptime, "slot":"settings-2500-png", "index":last ? count - 1 : 0, "count":count, "bytes":2_000_000, "sha256":String(repeating:"f",count:64), "data":payload.base64EncodedString()]
    return try JSONSerialization.data(withJSONObject:["settingsDiagnostic":record], options: slashless ? [.sortedKeys,.withoutEscapingSlashes] : [.sortedKeys])
}
let extremes: [Double] = [0, -0.0, Double.leastNonzeroMagnitude, Double.leastNormalMagnitude, Double.greatestFiniteMagnitude, 943842.1664629584]
var rows: [[String:Any]] = []
for n in [3072,4096,4992] {
    for slashless in [false,true] {
        for uptime in extremes {
            let data = try body(n, chunkSize:n, slashless:slashless, uptime:uptime)
            let decoded = try JSONSerialization.jsonObject(with:data) as! [String:Any]
            let record=decoded["settingsDiagnostic"] as! [String:Any]
            let payload=Data(base64Encoded:record["data"] as! String)!
            precondition(payload == Data(repeating:255,count:n))
            if slashless { precondition(data.count <= 8192) }
            rows.append(["decodedChunkBytes":n,"withoutEscapingSlashes":slashless,"uptime":String(uptime),"bodyBytes":data.count,"base64Bytes":4*((n+2)/3),"nonDataBytes":data.count-4*((n+2)/3),"roundTripPayloadUnchanged":true])
        }
    }
}
for n in [1,4095,4096,4991,4992] {
    let data=try body(n,chunkSize:4992,slashless:true,uptime:Double.greatestFiniteMagnitude,last:true)
    precondition(data.count<=8192)
    rows.append(["lastChunkBytes":n,"withoutEscapingSlashes":true,"bodyBytes":data.count])
}
let output=try JSONSerialization.data(withJSONObject:["scope":"Finite Foundation serializer probe only; no product/client/runtime code executed", "rows":rows],options:[.sortedKeys,.prettyPrinted,.withoutEscapingSlashes])
FileHandle.standardOutput.write(output)
FileHandle.standardOutput.write(Data([10]))
