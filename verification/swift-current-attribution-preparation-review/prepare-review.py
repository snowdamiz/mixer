#!/usr/bin/env python3
"""Reconstruct only sealed source into this independent review lane."""
from pathlib import Path
import ast,copy,datetime,hashlib,json,shutil,tarfile
H=Path(__file__).resolve().parent;R=H.parent.parent
P=H.parent/'swift-current-attribution-full-preparation';C=H.parent/'swift-cache-current-attribution-observer'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
save=lambda n,v:(H/n).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
assert sha(P/'prepared-seal.json')=='c40ab937f218baa54b45e5a5846e4dd12d05edcfb2c3786a75d27f026f70a7f1'
seal=json.loads((P/'prepared-seal.json').read_bytes())
assert len(seal['files'])==104
for n,d in seal['files'].items():assert sha(P/n)==d,n
for n,d in seal['externalFiles'].items():assert sha(R/n)==d,n
assert not (H/'owned-source').exists() and not (H/'owned-target').exists() and not (H/'owned-tmp').exists()
snap=H/'input-snapshots';snap.mkdir(exist_ok=True)
for n in ('diagnostic.py','telemetry.py','harness.rs','adapter.rs','adapter-controls.rs','prepared-seal.json','binding.json','root-selection-template.json','output-contract.json','restore.py'):
    shutil.copyfile(P/n,snap/n)
for n in ('AGENTS.md','PLAN.md'):
    shutil.copyfile(R/n,snap/n)
with tarfile.open(C/'isolated-source.tar.gz','r:gz') as t:
    members=t.getmembers();assert len(members)==132 and len({m.name for m in members})==132
    assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
    source={m.name:t.extractfile(m).read() for m in members}
accepted=json.loads((C/'copied-source-manifest.json').read_text())
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==accepted
test='src/experimental_swift_reactor/cache_tests.rs';life='src/experimental_swift_reactor/lifecycle_tests.rs'
source[test]+=b'\n'+(P/'adapter.rs').read_bytes()+b'\n'+(P/'adapter-controls.rs').read_bytes()
source[life]+=('\n// Isolated diagnostic only; baseline production bytes are unchanged.\ninclude!('+json.dumps(str(P/'harness.rs'))+');\n').encode()
prepared=json.loads((P/'copied-build-manifest.json').read_text())
assert {n:hashlib.sha256(b).hexdigest() for n,b in source.items()}==prepared
source[test]+=b'\n'+(H/'independent-controls.rs').read_bytes()
review={n:hashlib.sha256(b).hexdigest() for n,b in source.items()}
for n,b in source.items():
    out=H/'owned-source'/n;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(b)
(H/'owned-tmp').mkdir(mode=0o700)
save('review-source-manifest.json',review)
old=(H.parent/'swift-exact-reactor-after-plan-reuse/diagnostic.py').read_text();new=(P/'diagnostic.py').read_text()
f=lambda s:{n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
of,nf=f(old),f(new)
unchanged=['observe_group','record_command','strict_json','events','cleanup','build','host_controls']
assert all(of[n]==nf[n] for n in unchanged)
old_h=(H.parent/'swift-exact-reactor-after-plan-reuse/harness.rs').read_text();new_h=(P/'harness.rs').read_text()
assert old_h.split('    #[test]\n    fn exact_reactor_target_once()',1)[1]==new_h.split('    #[test]\n    fn exact_reactor_target_once()',1)[1]
save('source-audit.json',{'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preparedSealSHA256':sha(P/'prepared-seal.json'),'sealedFiles':104,'sourceFiles':132,'candidateManifestSHA256':sha(P/'copied-build-manifest.json'),'reviewManifestSHA256':sha(H/'review-source-manifest.json'),'independentChangedFiles':[n for n in prepared if prepared[n]!=review[n]],'originalTargetTestByteIdentical':True,'literalUnchangedHistoricalFunctions':unchanged,'externalHarness':{'path':str(P/'harness.rs'),'sha256':sha(P/'harness.rs')},'inputSnapshots':{n.name:sha(n) for n in snap.iterdir()},'liveVmRead':False,'gitQueried':False,'targetExecuted':False})
# Preserve exact inputs, rather than just prose claims, for the discovered validity gap.
original=json.loads((P/'control-001-events.json').read_text());rows=json.loads((P/'control-001-telemetry.json').read_text())['snapshots']
save('parser-original-events.json',original)
fixtures=H/'parser-reproductions';fixtures.mkdir(exist_ok=True)
for mode in ('integer_as_float','bool_sequence','negative_credit','wrong_calls_length','unknown_aggregate','invalid_first_rejection'):
    changed=copy.deepcopy(rows)
    if mode=='integer_as_float':changed[0]['reset_count']=1.0;changed[0]['payload']['credits']=[float(v) for v in changed[0]['payload']['credits']]
    if mode=='bool_sequence':changed[0]['sequence']=True
    if mode=='negative_credit':changed[0]['payload']['credits'][1]=-1;changed[0]['payload']['credits'][2]+=1
    if mode=='wrong_calls_length':changed[0]['payload']['calls'] += [99]
    if mode=='unknown_aggregate':changed[0]['payload']['unbound']=0
    if mode=='invalid_first_rejection':changed[0]['payload']['first_rejection']='bad'
    (fixtures/(mode+'.stdout')).write_text(''.join('MIXER_ATTRIBUTION '+json.dumps(r,separators=(',',':'))+'\n' for r in changed))
print(json.dumps({'preparedSealSHA256':sha(P/'prepared-seal.json'),'sourceFiles':132,'reviewManifestSHA256':sha(H/'review-source-manifest.json'),'sourceChangesFromCandidate':1,'targetExecuted':False},sort_keys=True))
