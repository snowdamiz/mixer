from pathlib import Path
import json,hashlib,subprocess,datetime
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];bindings={};git_checks=0
def bind(p,expected=None):
    h=hashlib.sha256(p.read_bytes()).hexdigest();assert expected is None or expected==h,str(p)
    bindings[str(p.relative_to(ROOT))]=h;return h
old=HERE/'original-HostTests.swift';old_hash=bind(old)
revision='c687e69e0b23199c632e89e8fec68741530dcdef'
assert hashlib.sha256(subprocess.check_output(['git','show',revision+':verification/android-binding-stage4/HostTests.swift'],cwd=ROOT)).hexdigest()==old_hash
fresh=[]
for mode in ['debug','release','tsan']:
    path=HERE/(mode+'-receipt.json');bind(path);r=json.loads(path.read_text())
    assert r['status']=='passed' and len(r['cases_executed'])==39
    for p,h in r['input_files'].items():bind(ROOT/p,h)
    for c in r['commands']:
        assert c['exit']==0
        log=HERE/(mode+'-logs')/Path(c['log']).name;bind(log,c['sha256'])
        assert b'WARNING: ThreadSanitizer' not in log.read_bytes()
    bind(Path(r['native_receipt']),r['native_receipt_sha256'])
    for p,h in r['native_inputs'].items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
    fresh.append({'mode':mode,'receipt_sha256':bind(path),'scenarios':39,'native_revision':r['native_source_revision'],'source_revision':r['revision'],'source_tree_sha256':r['source_tree_sha256']})
for mode in ['debug','release','tsan']:
    directory=HERE/'failed-hosted-artifact'/('android-binding-'+mode)
    r=json.loads((directory/'receipt.json').read_text());bind(directory/'receipt.json')
    assert r['revision']==revision
    for p,h in r['input_files'].items():
        assert hashlib.sha256(subprocess.check_output(['git','show',revision+':'+p],cwd=ROOT)).hexdigest()==h,p
        git_checks+=1
    for c in r['commands']:bind(directory/'logs'/Path(c['log']).name,c['sha256'])
    if mode=='tsan':
        assert r['status']=='failed' and r['commands'][-1]['name']=='fault-leave' and r['commands'][-1]['exit']==-5
        assert r['input_files']['verification/android-binding-stage4/HostTests.swift']==old_hash
    else:assert r['status']=='passed' and len(r['cases_executed'])==39
schedule=json.loads((HERE/'schedule-receipt.json').read_text());bind(HERE/'schedule-receipt.json')
for p,h in schedule['inputs'].items():bind(ROOT/p,h)
for c in schedule['commands']:
    assert c['exit']==0;bind(ROOT/c['log'],c['sha256'])
for p in ['failed-hosted-jobs.json','failed-hosted-swift.log','qualify.py']:bind(HERE/p)
result={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'root','status':'qualified-local-test-repair-awaiting-independent-review','bindings':dict(sorted(bindings.items())),'binding_count':len(bindings),'hosted_git_input_checks':git_checks,'hosted_failure':{'revision':revision,'run':40029192271,'job':120672894545,'artifact':12534941392,'scenario':'fault-leave','mode':'tsan','exit':-5,'log':'test observation deadline; original helper hid the call-site line','cause_limit':'The retained log does not identify which wait timed out. Deterministic schedule demonstrates an admitted test race; it does not reconstruct the precise hosted execution.'},'fresh':fresh,'scope':['Only verification/android-binding-stage4/HostTests.swift changes; production Swift/C unchanged.','Real C schedule in Debug/Release/TSan: old completion-only admission permits pending1, leave0, fault0; idle admission yields pending0, real leave8, stickyfault8.','Fresh SwiftPM Swift/C/SDK source builds and locked dependencies pass all39 scenarios per Debug/Release/TSan.','Rust archive is separately receipt-bound and reused from d814055; it is not TSan instrumented or rebuilt here.','This qualifies host test sequencing, not JNI/Looper/physical-device/rendering/signing/FieldLog/GA behavior.']}
(HERE/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',len(bindings),'file bindings;',git_checks,'failed-hosted Git source checks;117 fresh scenarios')
