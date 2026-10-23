#!/usr/bin/env python3
"""Index completed independent executions without repeating product tests."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys
OUT=pathlib.Path(__file__).resolve().parent
SOURCE=OUT/'.local/source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for line in (OUT/'frozen-source.sha256').read_text().splitlines():
    expected,path=line.split('  ',1)
    assert sha(SOURCE/path)==expected,path
for name,count in [('frozen-debug.log',37),('frozen-release.log',37),('implementation-tsan.log',24),('independent-debug-attempt-1.log',6),('independent-release.log',6),('independent-tsan.log',6)]:
    text=(OUT/name).read_text()
    assert f'Test run with {count} tests' in text and 'passed after' in text,name
    assert 'WARNING: ThreadSanitizer' not in text and 'ThreadSanitizer: data race' not in text,name
negative=(OUT/'public-substitution-rejected.log').read_text()
assert "cannot convert value of type 'SubstituteHTTP' to expected argument type 'URLSessionHTTPTransport'" in negative
assert "cannot convert value of type 'SubstituteStore' to expected argument type 'AppPrivateKeyValueStore'" in negative
commands=[
    {'command':['/usr/bin/swift','test','--package-path',str(SOURCE/'capabilities'),'--scratch-path',str(OUT/'.local/debug')],'exit_code':0,'output':'frozen-debug.log','tests':37},
    {'command':['/usr/bin/swift','test','--package-path',str(SOURCE/'capabilities'),'-c','release','--scratch-path',str(OUT/'.local/release')],'exit_code':0,'output':'frozen-release.log','tests':37},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/probe')],'exit_code':0,'output':'independent-debug-attempt-1.log','tests':6},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/probe'),'-c','release'],'exit_code':0,'output':'independent-release.log','tests':6},
    {'command':['/usr/bin/swift','test','--package-path',str(OUT/'.local/probe'),'--scratch-path',str(OUT/'.local/independent-tsan'),'--sanitize','thread'],'exit_code':0,'output':'independent-tsan.log','tests':6},
    {'command':['/usr/bin/swift','test','--package-path',str(SOURCE/'capabilities'),'--scratch-path',str(OUT/'.local/implementation-tsan'),'--sanitize','thread','--filter','NativeCapabilityExitTests|NativeHTTPTransportTests'],'exit_code':0,'output':'implementation-tsan.log','tests':24},
    {'command':['/usr/bin/swift','build','--package-path',str(OUT/'.local/negative')],'exit_code':1,'expected_exit_code':1,'output':'public-substitution-rejected.log','scope':'Intentional external-client compile rejection; custom protocol conformers cannot replace concrete installed adapters'},
    {'command':['python3',str(OUT/'audit.py')],'exit_code':0,'output':'evidence-audit-run.log'},
]
for entry in commands:entry['output_sha256']=sha(OUT/entry['output'])
tools={}
for name,args in {'swift':['/usr/bin/swift','--version'],'xcode':['/usr/bin/xcodebuild','-version'],'git':['git','--version'],'python':[sys.executable,'--version'],'developer_directory':['/usr/bin/xcode-select','-p']}.items():
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    tools[name]={'command':args,'exit_code':p.returncode,'output':p.stdout.decode()}
(OUT/'tools.json').write_text(json.dumps(tools,indent=2)+'\n')
files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and '.local' not in p.relative_to(OUT).parts and '__pycache__' not in p.relative_to(OUT).parts and p.name not in {'receipt.json','review-evidence.sha256'}]
manifest=''.join(sha(path)+'  '+path.relative_to(OUT).as_posix()+'\n' for path in files)
(OUT/'review-evidence.sha256').write_text(manifest)
audit=json.loads((OUT/'evidence-audit.json').read_text())
receipt={'schema':1,'status':'passed scoped independent installed native capability exit review','revision':json.loads((OUT/'freeze.json').read_text())['revision'],'source_freeze':json.loads((OUT/'freeze.json').read_text()),'qualified_source_digest':audit['qualified_source_digest'],'frozen_source_unchanged_after_execution':True,'tools':tools,'commands':commands,'independent_tests':{'source':'IndependentExitProbe.swift','source_sha256':sha(OUT/'IndependentExitProbe.swift'),'debug':6,'release':6,'thread_sanitizer':6},'implementation_tests_replayed':{'debug':37,'release':37,'native_http_exit_thread_sanitizer':24},'evidence_audit':'evidence-audit.json','findings':[],'review_evidence_manifest':'review-evidence.sha256','review_evidence_manifest_sha256':hashlib.sha256(manifest.encode()).hexdigest(),'review_evidence_files':len(files),'scope':'Independent frozen-source tests, lifetime/ordering/reentrancy/admission/static trust review, intentional compiler rejection and existing cross-build/codec evidence audit. No live mutable product sources used for test execution.','limitations':['URLProtocol fixtures bypass real TLS/network parsing','ThreadSanitizer covers owned code only, system frameworks opaque','Exit proves documented per-operation native cleanup and invocation return, not kernel/socket/RSS/global quiescence or stack unwinding','Storage terminal cancellation is not durable mutation rollback','Installed adapter construction alone does not bind release identity/configuration/grants'],'pending':['physical iOS/Android lifecycle/trust/runtime packaging (phones disconnected)','immutable separate-repository package/FieldLog consumption','guest/Rust/C mailbox integration','global process/session quota and no-unwind proof','activation/OTA qualification','signing/stores/accountable GA review'],'observed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(OUT/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'status':receipt['status'],'revision':receipt['revision'],'tests':receipt['independent_tests'],'files':len(files),'findings':receipt['findings']},indent=2))
