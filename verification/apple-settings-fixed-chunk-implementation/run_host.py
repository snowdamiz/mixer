"""Compile bounded Foundation host probes; never compile or run UIKit/XCTest."""
import hashlib,json,pathlib,shutil,subprocess,sys,time
B=pathlib.Path(__file__).resolve().parent
COMPILER=pathlib.Path('/Applications/Xcode_26.6.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/swiftc')
SDK='/Applications/Xcode_26.6.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk'
SCRATCH=B/'owned-host-scratch'
sha=lambda b:hashlib.sha256(b).hexdigest()

def generate():
 original=(B/'sources/accepted/harness/UITests/ToggleUITests.swift').read_text()
 klass=original[original.index('private final class SettingsTelemetry'):original.index('\nprivate final class CompletionObserver')]
 start=klass.index('    private func post(');end=klass.index('    func start()',start)
 expression='try JSONSerialization.data(withJSONObject: ["settingsDiagnostic": record], options: [.sortedKeys, .withoutEscapingSlashes])'
 assert original.count(expression)==1
 stub='''    static var hostRecords: [[String:Any]] = []
    static var hostReply: [String:Any] = [:]
    private func post(_ record:[String:Any]) throws -> [String:Any] {
        let body = EXPRESSION
        guard body.count <= 8192 else { throw Failure.upload }
        Self.hostRecords.append(record)
        if record["kind"] as? String == "start" { return Self.hostReply }
        if record["kind"] as? String == "observe" {
            let files = record["files"] as! [String:Any]
            return ["pending": ["ax","png"].filter { files[$0] != nil }.map { "settings-" + String(format:"%04d",record["sequence"] as! Int) + "-" + $0 }]
        }
        return ["accepted":true]
    }
'''.replace('EXPRESSION',expression)
 klass=klass[:start]+stub+klass[end:]
 return 'import Foundation\nimport CoreFoundation\nimport CryptoKit\n'+klass+'\n'+(B/'host_probe_tail.swift').read_text()

def main():
 SCRATCH.mkdir(exist_ok=False);commands=[];passed=False
 def run(argv,name,timeout):
  began=time.monotonic();p=subprocess.Popen(argv,cwd=B,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:out,err=p.communicate(timeout=timeout)
  except BaseException:
   p.kill();out,err=p.communicate();raise
  finally:
   if p.poll() is None:p.kill();p.wait()
  (B/(name+'.stdout')).write_bytes(out);(B/(name+'.stderr')).write_bytes(err)
  commands.append(dict(argv=argv,pid=p.pid,exitCode=p.returncode,elapsedSeconds=time.monotonic()-began,stdoutEOF=True,stderrEOF=True,ownedProcessReaped=p.poll() is not None,stdoutSHA256=sha(out),stderrSHA256=sha(err)))
  if p.returncode:raise RuntimeError(name+' failed; retained output')
  return out
 try:
  source=generate();(B/'generated_host_probe.swift').write_text(source);(SCRATCH/'main.swift').write_text(source)
  run([str(COMPILER),'--version'],'swift-version',15)
  run([str(COMPILER),'-sdk',SDK,'-target','arm64-apple-macosx26.0','-module-cache-path',str(SCRATCH/'module-cache'),str(SCRATCH/'main.swift'),str(B/'sources/accepted/harness/UITests/DiagnosticTransport.swift'),str(B/'sources/accepted/harness/UITests/SettingsFailureDiagnostic.swift'),'-o',str(SCRATCH/'host-probe')], 'host-compile',50)
  raw=run([str(SCRATCH/'host-probe')],'host-probe',20)
  report=json.loads(raw);assert report['passed'] is True
  (B/'host-controls.json').write_bytes(raw);passed=True
 finally:
  shutil.rmtree(SCRATCH)
  receipt=dict(schema=1,passed=passed,python=sys.version,compilerSHA256=sha(COMPILER.read_bytes()),runnerSHA256=sha(pathlib.Path(__file__).read_bytes()),commands=commands,sourceSHA256=sha((B/'generated_host_probe.swift').read_bytes()),ownedScratchAbsent=not SCRATCH.exists(),scope='Foundation serialization and derived client methods with post replaced by an in-process stub; original DiagnosticTransport/SettingsFailureDiagnostic host compiled. No UIKit/XCTest typecheck, listener, networking, native product or device.')
  (B/'host-command-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({'passed':passed,'ownedScratchAbsent':not SCRATCH.exists()}))
if __name__=='__main__':main()
