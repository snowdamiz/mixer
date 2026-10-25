private extension SettingsTelemetry {
    var acceptedGeneration: String { generation }
    func reviewPost(_ record:[String:Any]) throws -> [String:Any] { try post(record) }
}
private func check(_ ok: @autoclosure () -> Bool, _ why:String) { precondition(ok(),why) }
private func rejects(_ why:String,_ action:() throws -> Void) {
    do { try action(); preconditionFailure("unexpected acceptance: "+why) } catch {}
}
private func sha(_ data:Data)->String { SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined() }
private func response(_ literal:String?)->Data {
    Data(("{\"generation\":\"01234567-0123-4123-8123-0123456789ab\",\"remainingSessionSeconds\":1"+(literal.map{",\"chunkBytes\":"+$0} ?? "")+"}").utf8)
}
private func clear() { SettingsTelemetry.reviewRecords=[];SettingsTelemetry.reviewBodies=[] }
private var rows:[[String:Any]]=[]
for literal in [nil,"null","true","false","\"4992\"","4992.0","4992e0","4.992e3","3072","4993","0","-1","[]","{}"] as [String?] {
    let client=SettingsTelemetry();clear();SettingsTelemetry.reviewReply=response(literal)
    rejects("invalid echo "+(literal ?? "missing")){try client.start()}
    check(client.acceptedGeneration.isEmpty,"invalid echo accepted generation")
    check(SettingsTelemetry.reviewRecords.count==1,"unexpected retry/fallback")
    check(SettingsTelemetry.reviewRecords[0]["chunkBytes"] as? Int==4992,"client start format")
    rows.append(["control":"raw-json-echo-reject","literal":literal ?? "missing","generationUnaccepted":true,"posts":1])
}
SettingsTelemetry.reviewReply=response("4992")
do {let c=SettingsTelemetry();try c.start();check(!c.acceptedGeneration.isEmpty,"exact echo not accepted")}
for (form,limits) in [("ax",[1,4991,4992,4993,9984,200000]),("png",[1,4991,4992,4993,9984,2000000])] {
    for size in limits {
        let c=SettingsTelemetry();clear();try c.start()
        let payload=Data((0..<size).map{UInt8($0%256)})
        _=try c.observe("review-host-stub",routeIndex:0,attempt:0,snapshot:[:],started:0,finished:0,ax:form=="ax" ? payload:nil,png:form=="png" ? payload:nil)
        let parts=SettingsTelemetry.reviewRecords.filter{$0["kind"] as? String=="chunk"}
        let count=(size+4991)/4992;check(parts.count==count,"chunk count")
        var combined=Data()
        for (index,record) in parts.enumerated() {
            check(record["index"] as? Int==index,"chunk index")
            check(record["count"] as? Int==count,"descriptor count")
            check(record["bytes"] as? Int==size,"descriptor bytes")
            check(record["sha256"] as? String==sha(payload),"descriptor SHA")
            check(record["chunkBytes"]==nil,"new per-chunk format")
            let encoded=record["data"] as! String;let bytes=Data(base64Encoded:encoded)!
            check(bytes.count==min(4992,size-index*4992),"decoded length")
            check(encoded==bytes.base64EncodedString(),"canonical padding")
            combined.append(bytes)
        }
        check(combined==payload,"client byte identity")
        check(SettingsTelemetry.reviewBodies.allSatisfy{$0.count<=8192},"actual body guard")
        check(SettingsTelemetry.reviewBodies.allSatisfy{!String(decoding:$0,as:UTF8.self).contains("\\/")},"slash escaped")
        rows.append(["control":"actual-client-packing","format":form,"bytes":size,"chunks":count,"sha256":sha(payload),"maximumBody":SettingsTelemetry.reviewBodies.map{$0.count}.max()!])
    }
}
let finite:[Double]=[0,-0.0,Double.leastNonzeroMagnitude,Double.leastNormalMagnitude,Double.greatestFiniteMagnitude,Double.leastNormalMagnitude.nextDown,Double.greatestFiniteMagnitude.nextDown,1e-7,1e-6,1e20,1e21,Double.pi]
var observed=0;var envelopes=0;var metadataBytes=0
for size in [1,2,4991,4992] {
    for pattern in [0,1] {
        let bytes=pattern==0 ? Data(repeating:255,count:size):Data((0..<size).map{UInt8($0%256)})
        for uptime in finite {
            let record:[String:Any]=["kind":"chunk","case":"public-settings-full-keyboard-access","generation":"01234567-0123-4123-8123-0123456789ab","sequence":2500,"uptime":uptime,"slot":"settings-2500-png","index":400,"count":401,"bytes":2000000,"sha256":String(repeating:"f",count:64),"data":bytes.base64EncodedString()]
            let body=try JSONSerialization.data(withJSONObject:["settingsDiagnostic":record],options:[.sortedKeys,.withoutEscapingSlashes])
            check(body.count<=8192,"finite envelope guard")
            let wire=String(decoding:body,as:UTF8.self)
            let marker=wire.range(of:"\"uptime\":")!
            let number=String(wire[marker.upperBound...].dropLast(2))
            metadataBytes=body.count-bytes.base64EncodedString().utf8.count-number.utf8.count
            check(metadataBytes==316,"closed metadata accounting")
            let decoded=try JSONSerialization.jsonObject(with:body) as! [String:Any]
            let saved=decoded["settingsDiagnostic"] as! [String:Any]
            check(Data(base64Encoded:saved["data"] as! String)==bytes,"envelope exact bytes")
            check(!String(decoding:body,as:UTF8.self).contains("\\/"),"slash-heavy escaping")
            observed=max(observed,body.count);envelopes+=1
        }
    }
}
// Exercise the retained 8192 guard through the generated post stub at and over it.
do {
    let c=SettingsTelemetry();clear();try c.start()
    let base:[String:Any]=["kind":"review","padding":""]
    let count=try JSONSerialization.data(withJSONObject:["settingsDiagnostic":base],options:[.sortedKeys,.withoutEscapingSlashes]).count
    _=try c.reviewPost(["kind":"review","padding":String(repeating:"/",count:8192-count)])
    check(SettingsTelemetry.reviewBodies.last!.count==8192,"body exact boundary")
    rejects("body guard8193"){_ = try c.reviewPost(["kind":"review","padding":String(repeating:"/",count:8193-count)])}
}
do {
    var transport=DiagnosticTransportState();transport.deadline=100
    let full=try transport.begin(now:90);check(full==2,"two second ceiling")
    let clipped=try transport.begin(now:99.75);check(clipped==0.25,"absolute deadline clipping")
    transport.requests=2500;rejects("request cap"){_ = try transport.begin(now:90)}
    var deadline=DiagnosticTransportState();deadline.deadline=100
    rejects("absolute deadline"){_ = try deadline.begin(now:100)}
    var response=DiagnosticTransportState()
    let exact=Data(("{}"+String(repeating:" ",count:8190)).utf8)
    _=try response.response(status:200,data:exact,networkError:nil)
    rejects("response cap"){_ = try response.response(status:200,data:exact+Data([32]),networkError:nil)}
    let original=response.firstFailure
    _=response.latch(.network("later"));check(response.firstFailure==original,"sticky first failure")
    rejects("sticky begin"){_ = try response.begin(now:0)}
}
let result:[String:Any]=["passed":true,"controls":rows,"foundationEnvelopeRows":envelopes,"maximumFiniteEnvelopeBody":observed,"closedMetadataBytesExcludingUptimeAndData":metadataBytes,"finiteFloatExhaustive":false,"actualBodyGuard":8192,"body8192Accepted8193Rejected":true,"listener":false,"network":false,"native":false,"postAdapter":"explicit in-process stub; exact start/send/observe methods and serialization; not asynchronous URLSession evidence"]
let report=try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
try report.write(to:URL(fileURLWithPath:"foundation-controls.json"))
print(String(decoding:report,as:UTF8.self))
