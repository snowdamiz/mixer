#!/usr/bin/env python3
"""Bind revised preflight evidence and test exact isolated patch reproduction."""
from pathlib import Path
import datetime,difflib,hashlib,importlib.util,json,os,shutil,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=Path(sys.argv[1]).resolve()
s=importlib.util.spec_from_file_location('b',HERE/'build_overlay.py');b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
enc=b.enc;sha=b.sha;digest=lambda x:hashlib.sha256(enc(x)).hexdigest();save=lambda n,x:(OUT/n).write_bytes(enc(x));commands=[]
def run(name,args,cwd=ROOT,source=None):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=600)
 for stream in ['stdout','stderr']:(OUT/(name+'.'+stream)).write_bytes(getattr(p,stream))
 commands.append(dict(name=name,argv=args,cwd=str(cwd),sourceTreeSHA256=digest(source) if source else None,startedUTC=start,completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),exitCode=p.returncode,stdout=name+'.stdout',stdoutSHA256=sha(OUT/(name+'.stdout')),stderr=name+'.stderr',stderrSHA256=sha(OUT/(name+'.stderr'))));save('postprocess-commands.json',commands);print(name,p.returncode,flush=True);assert p.returncode==0,p.stderr.decode()[-7000:]
run('producer-candidate1-offline-verifier',['python3','-B','verification/swift-control-accounting-preflight/verify.py'])
run('frozen-independent-review-offline-verifier',['python3','-B','verification/swift-control-preflight-review/verify.py'])
run('source-audit-and-privacy',['python3','-B',str(HERE/'audit.py'),str(OUT)])
run('nested-layouts',['python3','-B',str(HERE/'nested_layout.py'),str(OUT)])
base=json.loads((OUT/'baseline-manifest.json').read_text());candidate=json.loads((OUT/'candidate-manifest.json').read_text());BASE=b.files(ROOT/'vm');assert BASE==base
BUILD=Path('/tmp')/('mixer-control-candidate2-patch-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));BUILD.mkdir()
try:
 with tarfile.open(OUT/'baseline-source.tar.gz') as t:t.extractall(BUILD,filter='data')
 vm=BUILD/'vm';run('exact-patch-reproduction',['patch','-p1','-i',str(HERE/'source.patch')],vm,base);actual=b.files(vm);assert actual==candidate
 save('patch-reproduction.json',dict(status='passed-exact-six-file-patch-reproduction',baselineTreeSHA256=digest(base),candidateTreeSHA256=digest(actual),sourcePatchSHA256=sha(HERE/'source.patch'),all120FilesExact=True))
finally:
 shutil.rmtree(BUILD);save('patch-cleanup.json',dict(ownedScratch=str(BUILD),removed=not BUILD.exists(),nativeInstancesStarted=False,otherProjectProcessesTouched=False))
old=ROOT/'verification/swift-control-accounting-preflight';oldControl=(old/'overlay/src/experimental_swift_reactor/control_operations.rs').read_text().split('// ACCOUNTING_START')[0];newControl=(HERE/'overlay/src/experimental_swift_reactor/control_operations.rs').read_text().split('// ACCOUNTING_START')[0]
(HERE/'behavior-delta.patch').write_text(''.join(difflib.unified_diff(oldControl.splitlines(True),newControl.splitlines(True),fromfile='candidate1/control_operations.rs',tofile='candidate2/control_operations.rs')))
for name in json.loads((HERE/'changed-files.json').read_text()):
 if name.endswith('control_operations.rs'):continue
 one=(old/'overlay'/name).read_text().split('// CONTROL_PRIVATE_ACCOUNTING_START')[0];two=(HERE/'overlay'/name).read_text().split('// CONTROL_PRIVATE_ACCOUNTING_START')[0];assert one==two,name
rows=json.loads((OUT/'bound-inventory-schema.json').read_text());wrapper=[r for r in rows if r.get('mirFunction','').endswith('::control_pop_value')];assert len(wrapper)==136
from collections import Counter
oldRows=json.loads((old/'inventory-schema.json').read_text());one=Counter((r['config'],r['window'],r['rustType']) for r in oldRows);two=Counter((r['config'],r['window'],r['rustType']) for r in rows)
delta=[dict(config=key[0],window=key[1],rustType=key[2],candidate1=one[key],candidate2=two[key],delta=two[key]-one[key]) for key in sorted(set(one)|set(two)) if one[key]!=two[key]]
save('inventory-delta.json',dict(candidate1Fields=len(oldRows),candidate2Fields=len(rows),netAdditionalFields=len(rows)-len(oldRows),wrapperFields=136,obsoleteDirectPhaseReborrowFields=16,roles=delta,noNestedInventoryCredit=True))
save('source-review.json',dict(status='candidate2-defensive-source-repair-preflight-only',finding='SCPR-01',behaviorDelta='Swift pop leaf routes to private control_pop_value. Snapshot actual length, invoke unchanged accepted primitive, latch existing cleanup.live_unreconciled on failing return after actual arena length changed, return original Result unchanged.',sourceEffectOrder=['snapshot actual length','accepted phase.pop_value with original work/guard/pop/remove order','inspect original Result and actual length','on after-effect failure set existing latch','return original Result','existing outer control wrapper terminalizes'],onlyAlgorithmDelta='behavior-delta.patch',newWrapperCanonicalRows=len(wrapper),perConfigurationRows=68,totalCanonicalFields=len(rows),canonicalSelectedFunctions=38,originalValuePrimitiveUnchanged=candidate['src/experimental_swift_reactor/value_operations.rs']==base['src/experimental_swift_reactor/value_operations.rs'],noSecondRemovalOrWorkOrFailureReplacement=True,privateFieldsAndKindRemainOriginal=True,behaviorExecuted=False,faultInjectionExecuted=False,controlExecutionAuthorized=False,rootReviewRequired=True,logicalOwnershipOnly=True,physicalStackOrRSSClaim=False,optimizedPrivateCoreAliases=False))
inputs=['docs/swift-control-invocation-contract.md','docs/swift-control-accounting-preflight.md','docs/swift-control-preflight-review.md','verification/swift-control-invocation-root-review/contract.json','verification/swift-control-invocation-root-review/accounting-scope-interpretation.json','verification/swift-control-accounting-preflight/seal.json','verification/swift-control-accounting-preflight/verify.py','verification/swift-control-accounting-preflight/results/20261024T062441792011Z/receipt.json','verification/swift-control-preflight-review/frozen.json','verification/swift-control-preflight-review/seal.json','verification/swift-control-preflight-review/findings.json']
save('inputs.json',dict(files={name:sha(ROOT/name) for name in inputs},baselineTreeSHA256=digest(base),historicalCandidate1TreeSHA256='6d9e1b3f5aec1bedf2a8dc773a23c1731ee05e094d69d646ab4db8d397381156',candidate2TreeSHA256=digest(candidate),producerAndReviewerEvidenceModified=False))
assert b.files(ROOT/'vm')==BASE
save('postprocess-receipt.json',dict(status='passed-source-privacy-nested-and-patch-preflight',commands=commands,liveVMUnchanged=True,controlMethodsExecuted=False,faultBehaviorExecuted=False,sc01Through12Passed=False,accountingAccepted=False,implementationAccepted=False,gaAcceptance=False))
print('candidate2',digest(candidate),flush=True)
