#!/usr/bin/env python3
"""Seal only owned independent review artifacts, leaving root-* files outside."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
DOC=ROOT/'docs/swift-count-plan-retention-candidate-review.md'
PRODUCER=ROOT/'verification/swift-count-plan-retention-candidate'
EXPECTED_SEAL='29601717bcdc4c8a6c1de9c80ab2d26fdcc04c265b799dfa7e07868d541eb8a1'
EXPECTED_LIVE='16176e0852fa61cba98acebeb373ee1a6be4c686d0e46ef8bbc144c0527c2cbd'
def sha(data): return hashlib.sha256(data).hexdigest()
def js(path): return json.loads(path.read_bytes())
def write(path,value): path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
assert sha((PRODUCER/'seal.json').read_bytes())==EXPECTED_SEAL
for member in js(PRODUCER/'seal.json')['members']:
    data=(ROOT/member['path']).read_bytes()
    assert len(data)==member['bytes'] and sha(data)==member['sha256']
names=js(PRODUCER/'baseline-source-manifest.json')
live={name:sha((ROOT/'vm'/name).read_bytes()) for name in names}
assert live==names
assert sha((json.dumps(live,indent=2,sort_keys=True)+'\n').encode())==EXPECTED_LIVE
for directory in sorted((OUT/'commands').glob('audit-*')):
    command,result=js(directory/'command.json'),js(directory/'result.json')
    assert sha((directory/'source.py').read_bytes())==command['sourceSHA256']
    assert sha((directory/'audit-results.json').read_bytes())==result['auditResultSHA256']
    for stream in ['stdout','stderr']:
        data=(directory/stream).read_bytes()
        assert len(data)==result[stream+'Bytes'] and sha(data)==result[stream+'SHA256']
    assert result['liveClosureAfter']==command['liveClosureBefore']==EXPECTED_LIVE
    assert result['producerSealSHA256After']==command['producerSealSHA256']==EXPECTED_SEAL
final_command=js(OUT/'commands/audit-02/command.json')
final_result=js(OUT/'commands/audit-02/result.json')
audit=js(OUT/'audit-results.json')
assert final_result['exitCode']==0
assert (audit['testsRun'],audit['failures'],audit['errors'])==(23,0,0)
assert sha((OUT/'audit-results.json').read_bytes())==final_result['auditResultSHA256']
assert sha((OUT/'audit.py').read_bytes())==final_command['sourceSHA256']
for path in [DOC]+sorted(OUT.rglob('*')):
    if not path.is_file() or path.name.startswith('root-'): continue
    assert not path.is_symlink(),path
    if path.suffix in ['.py','.md']:
        text=path.read_text()
        assert text.endswith('\n'),path
        assert all(line.rstrip()==line for line in text.splitlines()),path
        if path.suffix=='.py': compile(text,str(path),'exec')
assert not (PRODUCER/'.scratch').exists()
revision=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevision':revision,
         'producerSealSHA256':EXPECTED_SEAL,'producerMembers':114,'liveClosureSHA256':EXPECTED_LIVE,'liveSourceFiles':132,
         'decision':'accept-recorded-rejection-only','candidateCorrectnessAccepted':False,'integrationSelected':False,
         'audit':{'command':'commands/audit-02/command.json','result':'commands/audit-02/result.json','passed':23,'failed':0,'errors':0,
                  'sourceSHA256':final_command['sourceSHA256'],'reportSHA256':final_result['auditResultSHA256']},
         'initialAudit':{'command':'commands/audit-01/command.json','passed':22,'failed':1,'errors':0,
                         'reason':'Auditor expected complete source token; rustc abbreviated source line. Corrected to complete diagnostic text.'},
         'producerRustCommands':{'total':14,'exitZero':11,'compileFailures':2,'suiteFailureCommands':1},
         'originalSwift':{'baselinePassed':39,'candidatePassed':37,'candidateFailed':2},
         'sourceChanges':'Only new owned review documentation and evidence; producer/live/root metadata untouched',
         'command':[sys.executable,'-B',str(pathlib.Path(__file__).resolve())],'cwd':str(ROOT),
         'python':{'path':sys.executable,'version':sys.version,'sha256':sha(pathlib.Path(sys.executable).read_bytes())},
         'finalizerSHA256':sha(pathlib.Path(__file__).read_bytes()),
         'checks':['producer114-member-seal','live132-file-closure','two-audit-command-stream/source/report-bindings',
                   'owned-Python-compile','owned-text-whitespace','producer-scratch-absent'],
         'freshRustReplay':'not run','fullTarget':'not run','nativeUIAndCapture':'not used; paused',
         'excludedHostedHarnesses':'not read/imported/executed','processDiscovery':'not performed',
         'cleanup':'No extracted source, compiler product, native instance or background process created; producer scratch absent',
         'limitations':['Finite result/evidence audit only','No candidate correctness or target-benefit acceptance',
                        'Physical/native/compiler/signing/store/provider/FieldLog-published-package/final-GA gates remain pending'],
         'sealExcludes':['seal.json','seal.sha256','every filename beginning root-']}
write(OUT/'receipt.json',receipt)
members=[]
for path in [DOC]+sorted(OUT.rglob('*')):
    if not path.is_file() or path.name in ['seal.json','seal.sha256'] or path.name.startswith('root-'): continue
    data=path.read_bytes();members.append({'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':sha(data)})
seal={'schema':1,'scope':'Independent recorded-rejection audit only; no candidate correctness or integration acceptance',
      'producerSealSHA256':EXPECTED_SEAL,'liveClosureSHA256':EXPECTED_LIVE,'sourceRevision':revision,
      'excludes':receipt['sealExcludes'],'members':members}
write(OUT/'seal.json',seal)
seal_sha=sha((OUT/'seal.json').read_bytes())
(OUT/'seal.sha256').write_text(seal_sha+'  seal.json\n')
for member in members:
    data=(ROOT/member['path']).read_bytes();assert len(data)==member['bytes'] and sha(data)==member['sha256']
print(json.dumps({'status':'sealed','members':len(members),'sealSHA256':seal_sha,
                  'receiptSHA256':sha((OUT/'receipt.json').read_bytes()),'docSHA256':sha(DOC.read_bytes()),
                  'liveClosureSHA256':EXPECTED_LIVE,'auditMethodsPassed':23},sort_keys=True))
