#!/usr/bin/env python3
"""Read-only verification of the one failed native attempt and retained cleanup."""
import hashlib,json,stat,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def check(n,r):
 p=ROOT/n;s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink(),n
 actual={'bytes':s.st_size,'sha256':sha(p),'mode':stat.S_IMODE(s.st_mode),'kind':'file'}
 assert all(actual[k]==v for k,v in r.items()),n
receipt=load(BASE/'result/receipt.json');manifest=load(BASE/'result/native-files.json')
assert sha(BASE/'result/native-files.json')==receipt['nativeManifestSHA256'] and len(manifest)==receipt['nativeFiles']==2257
for n,r in manifest.items():check(n,r)
for n,r in receipt['frozenInputsUnchanged'].items():
 p=ROOT/n;assert sha(p)==r['sha256'];handoff=load(p);assert len(handoff['members'])==r['members']
 for name,row in handoff['members'].items():check(name,row)
run=ROOT/'verification/apple-settings-instrumented-runtime-preparation'/('native-run-v6-'+receipt['runID'])
for p in (BASE/'result/retained').rglob('*'):
 if p.is_file():assert sha(p)==sha(run/p.relative_to(BASE/'result/retained')),p
assert not (Path('/Users/andreyyurlov/Library/Developer/CoreSimulator/Devices')/receipt['environment']['udid']).exists()
assert receipt['cleanupOperationsPassed']==5 and receipt['officialSummary']=={'failed':1,'passed':0,'skipped':1} and not receipt['nativeVerdictAccepted']
print(json.dumps({'status':'verified-failed-native-result','nativeFiles':len(manifest),'producerMembers':61,'reviewMembers':18,'cleanupOperations':5,'ownedSimulatorAbsent':True,'python':sys.version,'verifierSHA256':sha(Path(__file__))}))
