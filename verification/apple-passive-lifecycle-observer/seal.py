#!/usr/bin/env python3
"""Seal source-and-host prerequisite after owned scratch cleanup; never builds/runs UIKit."""
import datetime, hashlib, json, pathlib, subprocess, sys, time
HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def stable(v):return (json.dumps(v,indent=2,sort_keys=True)+'\n').encode()
assert not (HERE/'handoff.json').exists()
assert not (HERE/'scratch').exists() and not (HERE/'.host-work').exists()
started=datetime.datetime.now(datetime.timezone.utc).isoformat();start=time.monotonic()
argv=[sys.executable,'-B',str(HERE/'audit.py')]
p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=55)
(HERE/'seal-audit.stdout').write_bytes(p.stdout);(HERE/'seal-audit.stderr').write_bytes(p.stderr)
receipt={'schema':1,'name':'pre-seal-read-only-audit','argv':argv,'cwd':str(ROOT),'toolVersion':sys.version,'startedUTC':started,'elapsedSeconds':time.monotonic()-start,'timeoutSeconds':55,'exitCode':p.returncode,'stdoutSHA256':sha(p.stdout),'stderrSHA256':sha(p.stderr),'sourceArchiveSHA256':sha((HERE/'review-source-package.tar.gz').read_bytes()),'scope':'Source and finite host-evidence consistency only; no UIKit/native execution'}
(HERE/'seal-command-receipt.json').write_bytes(stable(receipt))
assert p.returncode==0,p.stderr.decode()
summary=json.loads(p.stdout)
files=[ROOT/'docs/apple-passive-lifecycle-observer.md']+sorted(p for p in HERE.rglob('*') if p.is_file())
members={str(p.relative_to(ROOT)):{'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in files}
handoff={'schema':1,'status':'source-and-finite-host-prerequisite-ready-for-independent-review','sourceContextRevision':'6b8aba350224ed19f678669bdbea6b359d8de68b','agentModelRequested':'gpt-6.1-sol','agentReasoningRequested':'xhigh','sourceArchiveSHA256':summary['sourceArchiveSHA256'],'candidateSourceMembers':42,'changedExistingSourceMembers':['accepted/source/Prototype/main.swift'],'addedSourceMembers':['accepted/source/Prototype/PassiveLifecycleData.swift','accepted/source/Prototype/PassiveLifecycleObserver.swift'],'unchangedSourceMembers':39,'hostMethods':summary['hostMethods'],'preSealReadOnlyChecks':summary['checks'],'inputFiles':summary['inputFiles'],'uikitCompiled':False,'genericSimulatorBuildSelected':False,'nativeExecution':False,'nativePassed':False,'gaAccepted':False,'historicalOfficialResult':{'settings':'Passed','firstTab':'Failed','xcodeExitCode':65},'physicalPhones':'disconnected-deferred','ownedScratchRemoved':True,'memberTreeSHA256':sha(stable(members)),'members':members}
(HERE/'handoff.json').write_bytes(stable(handoff))
print(json.dumps({k:v for k,v in handoff.items() if k!='members'},sort_keys=True))
