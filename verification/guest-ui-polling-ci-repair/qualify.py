#!/usr/bin/env python3
from pathlib import Path
import datetime,hashlib,io,json,os,re,subprocess,tarfile,time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;TREE=HERE/'tree';BUILD=HERE/'build';BASE='d81405559cc6bb50803a674f556eb61e75507940'
assert not TREE.exists();TREE.mkdir()
paths=['sdk/Package.swift','sdk/Sources','experimental-capability-runtime/Package.swift','experimental-capability-runtime/Sources','experimental-capability-runtime/Tests','experimental-capability-runtime/verification/with-loopback.py']
with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive',BASE,*paths],cwd=ROOT))) as tar:tar.extractall(TREE,filter='data')
sha=lambda b:hashlib.sha256(b).hexdigest()
testpath='experimental-capability-runtime/Tests/MixerExperimentalCapabilityRuntimeTests/GuestUITests.swift';old=(TREE/testpath).read_text();fixed=(ROOT/testpath).read_text();(HERE/'original-test.swift').write_text(old);(HERE/'fixed-test.swift').write_text(fixed)
(TREE/testpath).write_text(fixed)
manifest={str(p.relative_to(TREE)):sha(p.read_bytes()) for p in TREE.rglob('*') if p.is_file()}
(HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
native=BUILD/'native';(HERE/'native-receipt.json').write_bytes((native/'receipt.json').read_bytes())
receipt={'revision':BASE,'source_manifest_sha256':sha(json.dumps(manifest,sort_keys=True).encode()),'source_manifest':'verification/guest-ui-polling-ci-repair/source-manifest.json','source_overlay':{testpath:sha(fixed.encode())},'commands':[],'native_artifacts':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [native/'lib/libmixer_vm_capability_experimental.a',*sorted((native/'include').glob('*.h'))]},'scope':'Test-only bounded polling repair on frozen committed SDK/runtime and freshly built exact-revision native archive. Real timer handler/guest bridge; no physical devices. Local Swift6.4 differs from hosted Swift6.2.4. Controlled queue delay demonstrates the old wait assumption, not exact hosted scheduling cause. Rust/system libraries are not Swift TSan instrumented.','status':'running'}
def save(): (HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def run(name,argv,expected=0):
 start=time.monotonic();p=subprocess.run([str(x) for x in argv],cwd=TREE,env=os.environ|{'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 log=HERE/(name+'.log');log.write_bytes(p.stdout);text=p.stdout.decode(errors='replace');matches=re.findall(r'Test run with (\d+) tests? in \d+ suites? (passed|failed)',text)
 record={'name':name,'argv':[str(x) for x in argv],'cwd':str(TREE),'exit_code':p.returncode,'expected_exit':'nonzero' if expected else 'zero','seconds':time.monotonic()-start,'log':str(log.relative_to(ROOT)),'log_sha256':sha(p.stdout),'test_counts':matches};receipt['commands'].append(record);save();print(name,p.returncode,matches,text[-350:],flush=True)
 assert (p.returncode!=0)==bool(expected),name
 return text
run('swift-version',['swift','--version']);run('xcode-version',['xcodebuild','-version']);run('python-version',['python3','--version'])
package=TREE/'experimental-capability-runtime';flags=['-Xcc','-I'+str(native/'include'),'-Xlinker','-L'+str(native/'lib'),'-Xswiftc','-warnings-as-errors','-Xswiftc','-DMIXER_EXPERIMENTAL_LOCAL_TLS_TEST']
for mode,opts in [('debug',[]),('release',['-c','release']),('tsan',['--sanitize','thread'])]:
 command=['swift','test','--package-path',package,'--scratch-path',BUILD/mode,*opts,*flags]
 loopback=['python3','-B',package/'verification/with-loopback.py','--output',BUILD/(mode+'-tls'),'--']
 text=run('full-'+mode,loopback+command);assert re.search(r'Test run with 48 tests in 1 suite passed',text)
# Isolate one existing real-runtime scenario under an actually blocked serial queue.
gate='''        let pollingGate = GuestUIQueueGate()
        ExperimentalQueues.guest.async { pollingGate.hold() }
        defer { pollingGate.release() }
        try await bridgeEventually { pollingGate.entered }
'''
for variant,source in [('old',old),('fixed',fixed)]:
 source=source.replace('        let ticks = h.session.status.timerTicks\n',gate+'        let ticks = h.session.status.timerTicks\n')
 assertion='        #expect(h.session.status.timerTicks > ticks)'
 if variant=='old':source=source.replace(assertion,assertion+'\n        pollingGate.release()')
 else:source=source.replace('        // Dispatch timer delivery', '        try await Task.sleep(for: .milliseconds(35))\n        #expect(h.session.status.timerTicks == ticks)\n        pollingGate.release()\n        // Dispatch timer delivery')
 (HERE/('controlled-'+variant+'.swift')).write_text(source);(TREE/testpath).write_text(source)
 for mode,opts in [('debug',[]),('release',['-c','release'])]:
  text=run('controlled-'+variant+'-'+mode,['swift','test','--package-path',package,'--scratch-path',BUILD/mode,*opts,*flags,'--filter','guestUIIdlePollingCloseAndAcceptedInputRaceRemainBounded'],expected=variant=='old')
  assert re.search(r'Test run with 1 test in 1 suite '+('failed' if variant=='old' else 'passed'),text)
  if variant=='old':assert 'timerTicks' in text and 'Expectation failed' in text
(TREE/testpath).write_text(fixed)
assert sha((ROOT/testpath).read_bytes())==sha(fixed.encode())
for path,digest in manifest.items():assert sha((TREE/path).read_bytes())==digest,path
receipt['status']='passed';receipt['observed_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
