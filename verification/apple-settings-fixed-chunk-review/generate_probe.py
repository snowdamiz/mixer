#!/usr/bin/env python3
"""Use exact reviewed client methods; replace only network post with a named stub."""
import hashlib,json,pathlib
B=pathlib.Path(__file__).resolve().parent
p=B/'sources/accepted/harness/UITests/ToggleUITests.swift'
source=p.read_text();first=source.index('private final class SettingsTelemetry');last=source.index('\nprivate final class CompletionObserver')
klass=source[first:last];a=klass.index('    private func post(');b=klass.index('    func start()',a)
expression='try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes])'
assert source.count(expression)==1 and 'guard body.count <= 8192' in klass[a:b]
stub='''    static var reviewReply = Data()
    static var reviewRecords: [[String:Any]] = []
    static var reviewBodies: [Data] = []
    private func post(_ record:[String:Any]) throws -> [String:Any] {
        let body = EXPRESSION
        guard body.count <= 8192 else { throw Failure.upload }
        Self.reviewRecords.append(record); Self.reviewBodies.append(body)
        if record["kind"] as? String == "start" {
            return try transport.response(status:200,data:Self.reviewReply,networkError:nil)
        }
        if record["kind"] as? String == "observe" {
            let files=record["files"] as! [String:Any]
            return ["pending": files.keys.sorted().map { "settings-"+String(format:"%04d",record["sequence"] as! Int)+"-"+$0 }]
        }
        return ["accepted":true]
    }
'''.replace('EXPRESSION',expression)
out='import Foundation\nimport CoreFoundation\nimport CryptoKit\n'+klass[:a]+stub+klass[b:]+'\n'+(B/'probe_tail.swift').read_text()
(B/'independent-probe.swift').write_text(out)
(B/'probe-binding.json').write_text(json.dumps(dict(exactEndpointSHA256=hashlib.sha256(p.read_bytes()).hexdigest(),generatedSHA256=hashlib.sha256(out.encode()).hexdigest(),replacement='only SettingsTelemetry.post replaced with explicit in-process serialization/reply stub',retainedMethods=['start','send','mark','observe'],retainedBodyGuard=8192,networkExecuted=False),indent=2)+'\n')
print(json.dumps({'generated':True,'bytes':len(out.encode())}))
