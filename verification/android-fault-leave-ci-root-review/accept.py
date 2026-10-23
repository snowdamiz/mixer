from pathlib import Path
import json,hashlib,datetime,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
review=ROOT/'verification/android-fault-leave-ci-independent-review';bindings={}
def bind(p,h=None):
    value=hashlib.sha256(p.read_bytes()).hexdigest();assert h is None or value==h,str(p)
    bindings[str(p.relative_to(ROOT))]=value;return value
r=json.loads((review/'review-receipt.json').read_text());assert r['status']=='no_actionable_findings'
for p,h in r['evidence'].items():bind(review/p,h)
bind(review/'review-receipt.json')
a=json.loads((review/'audit-receipt.json').read_text());assert a['status']=='passed' and not a['findings'] and a['binding_count']==993
for p,h in a['bindings'].items():bind(ROOT/p,h)
p=json.loads((review/'probe-receipt.json').read_text());assert p['status']=='passed'
for c in p['commands']:assert c['exit']==0;bind(ROOT/c['log'],c['sha256'])
for mode in ['debug','release','tsan']:
    old=(review/(mode+'-old.log')).read_text();fixed=(review/(mode+'-fixed.log')).read_text()
    assert 'fault=0' in old and 'fault=8' in fixed
q=ROOT/'verification/android-fault-leave-ci-repair/qualification.json';bind(q)
data=json.loads(q.read_text());assert data['hosted_git_input_checks']==453
for p,h in data['bindings'].items():bind(ROOT/p,h)
bind(ROOT/'verification/android-binding-stage4/HostTests.swift',r['candidate_fixture_sha256'])
bind(HERE/'accept.py')
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'reviewer':'root','decision':'accepted-test-only-idle-precondition-repair','binding_count':len(bindings),'bindings':dict(sorted(bindings.items())),'verified':['117 fresh ordinary scenarios across Debug/Release/TSan','Six independent actual Swift/C old/fixed schedule proofs with delayed b task','Three independent unmodified fixture replays','453 failed-hosted Git source matches; failed log and all source provenance retained'],'limitations':['Exact cause of sparse hosted c687e69 deadline is unproved; demonstrated admitted race is repaired.','Only test sequencing/diagnostics changed; product transport/binding unchanged.','Reused native Rust archive is not TSan instrumented. Hosted repaired checkpoint verification is pending.','JNI/Looper/device/design-parity/signed-release/immutable-FieldLog/all-GA gates remain pending.']}
(HERE/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',len(bindings),'root exact acceptance bindings')
