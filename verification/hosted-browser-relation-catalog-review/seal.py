"""Seal independent review without modifying producer/product or root metadata."""
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
DOC = ROOT / 'docs/hosted-browser-relation-catalog-review.md'
commands = []


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree(values):
    return hashlib.sha256(''.join(p+'\t'+digest+'\n' for p,digest in sorted(values.items())).encode()).hexdigest()


def command(label, argv, success=True):
    result = subprocess.run(argv, cwd=ROOT, env=dict(os.environ,ERL_FLAGS='+S 2:2'), capture_output=True, text=True, timeout=30)
    (BASE / (label+'.stdout')).write_text(result.stdout)
    (BASE / (label+'.stderr')).write_text(result.stderr)
    commands.append({'label':label,'command':argv,'cwd':str(ROOT),'exit':result.returncode,'stdout':label+'.stdout','stderr':label+'.stderr'})
    if success:
        assert result.returncode == 0,label
    return result


command('seal-independent-audit',['python3','verification/hosted-browser-relation-catalog-review/audit.py'])
audit = json.loads((BASE/'audit.json').read_text())
for path,digest in audit['input_sha256'].items():
    assert sha(ROOT/path) == digest,path
compile_receipt = json.loads((BASE/'format-compile.json').read_text())
assert compile_receipt['passed'] and all(compile_receipt['cleanup'].values())
for path,digest in compile_receipt['source_sha256'].items():
    assert sha(ROOT/path)==digest,path
all_attempts=[]
for path in sorted((BASE/'attempts').glob('*/receipt.json')):
    receipt=json.loads(path.read_text())
    assert all(receipt['cleanup'].values()),path
    for name,digest in receipt['output_sha256'].items():
        assert sha(path.parent/name)==digest,(path,name)
    for name,digest in receipt['source_sha256'].items():
        assert sha(path.parent/'inputs'/name)==digest,(path,name)
    all_attempts.append((path,receipt))
selected=[]
for major in [16,17]:
    path,receipt=next((p,r) for p,r in reversed(all_attempts) if r['major']==major and r['success'] and all(sha(ROOT/name)==digest for name,digest in r['source_sha256'].items()))
    for name,digest in receipt['dependency_sha256'].items():
        assert sha(ROOT/name)==digest,name
    result=json.loads((path.parent/'checks.json').read_text())
    assert len(result['checks'])==96 and len(result['facts'])==18
    assert all(method['passed'] for method in result['checks'])
    selected.append({'major':major,'path':str(path.relative_to(ROOT)),'sha256':sha(path),'methods':len(result['checks']),'actual_denied_mutations':14,'actual_allowed_name_equivalences':2,'independent_observed_facts':len(result['facts']),'source_tree_sha256':receipt['source_tree_sha256'],'dependency_tree_sha256':receipt['dependency_tree_sha256'],'actual_server_version':(path.parent/'actual-server-version.stdout').read_text().strip(),'cleanup':receipt['cleanup']})
assert selected[0]['source_tree_sha256']==selected[1]['source_tree_sha256']
assert selected[0]['dependency_tree_sha256']==selected[1]['dependency_tree_sha256']

for label,argv in [('seal-mix-version',['mix','--version']),('seal-git-version',['git','--version']),('seal-python-version',['python3','--version']),('seal-revision',['git','rev-parse','HEAD'])]:
    command(label,argv)
cleanup={}
for i,(path,receipt) in enumerate(all_attempts):
    entry=dict(receipt['cleanup'])
    if receipt['major']==17:
        scratch=Path(receipt['owned_scratch'])
        entry['still_postmaster_absent']=not (scratch/'data/postmaster.pid').exists()
        entry['still_scratch_absent']=not scratch.exists()
    else:
        name=receipt['owned_container']
        result=command('seal-container-absence-'+str(i),['docker','container','inspect',name],success=False)
        entry['still_container_absent']=result.returncode!=0 and ('No such container' in result.stderr or 'No such object' in result.stderr)
    assert all(entry.values()),path
    cleanup[path.parent.name]=entry

artifacts={str(path.relative_to(ROOT)):sha(path) for path in sorted(BASE.rglob('*')) if path.is_file() and path.name!='receipt.json' and not path.name.startswith('root-')}
# Attempt receipts are immutable input records, unlike this top-level seal.
for path,_ in all_attempts:
    artifacts[str(path.relative_to(ROOT))]=sha(path)
artifacts[str(DOC.relative_to(ROOT))]=sha(DOC)
output={'schema':1,'status':'independent-review-passes-bounded-relation-prerequisite','recorded_at':dt.datetime.now(dt.timezone.utc).isoformat(),'source_revision':(BASE/'seal-revision.stdout').read_text().strip(),'scope':'Original-nine PG16/PG17 RelationCatalog private prerequisite only; root acceptance and all broader owner/runtime/GA gates remain separate.','blocking_findings':[],'producer_receipt':{'path':'verification/hosted-browser-relation-catalog/receipt.json','sha256':sha(ROOT/'verification/hosted-browser-relation-catalog/receipt.json')},'selected':selected,'source_audit_assertions':audit['passed'],'format_compile':'verification/hosted-browser-relation-catalog-review/format-compile.json','coverage':'verification/hosted-browser-relation-catalog-review/coverage-review.json','commands':commands,'seal_command':['python3','verification/hosted-browser-relation-catalog-review/seal.py'],'cleanup':cleanup,'artifact_sha256':artifacts,'artifact_tree_sha256':tree(artifacts),'retained_attempts':[{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'success':receipt['success'],'failure':receipt.get('failure'),'selected':any(s['path']==str(path.relative_to(ROOT)) for s in selected)} for path,receipt in all_attempts],'limitations':['Independent source assertions and 96 methods per major overlap in coverage; no 48-case runtime completion claim.','Fourteen independently observed denied fixture mutations and two allowed-name equivalents per major are transaction-local; fixture restoration is not Store rollback qualification.','Actual PG16 Docker Linux and PG17 native macOS C/libc UTF8/origin only; non-C/provider/version, Neon and operational index transitions remain unqualified.','Driver-error/throw/malformed result tests are adapter seams over clean actual results, not real server cancellation or pool-pressure evidence.','Trusted Store/Repo/checkout/role provenance, function/type conjunction and original checkout-to-commit deadline/rollback remain pending.','Timed row-decoder/final-return expiry, serialized operator DDL, provider/HTTP/console/customer/external immutable FieldLog packages and GA acceptance remain pending.','Pinned Oban source closure must exist at compilation; runtime uses embedded manifests and no verification fixture imports.','Native/UI/capture/runtime-device tests remain paused; no process discovery or other project resource changes occurred.'],'owned_paths_only':['docs/hosted-browser-relation-catalog-review.md','verification/hosted-browser-relation-catalog-review/']}
(BASE/'receipt.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':output['status'],'selected':selected,'receipt_sha256':sha(BASE/'receipt.json'),'artifact_tree_sha256':output['artifact_tree_sha256']},indent=2))
