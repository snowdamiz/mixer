"""Accept only the corrected partial callee interface, preserving all residuals."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = ROOT / 'verification/swift-guarded-snapshot-callee-source-correction-independent'
PRODUCER = ROOT / 'verification/swift-guarded-snapshot-provider-callee-source-correction'
OUT = HERE / 'callee-source-correction-root-check'
ACCEPT = HERE / 'guarded-snapshot-provider-callee-source-correction-host-acceptance.json'
sha = lambda b: hashlib.sha256(b).hexdigest()
def row(p):
    raw = p.read_bytes()
    return {'path':str(p.relative_to(ROOT)), 'bytes':len(raw), 'sha256':sha(raw)}
def save(p,v):
    with p.open('x') as f: json.dump(v,f,indent=2);f.write('\n')
def custody():
    result=[]
    for folder,digest,count,total in [(PRODUCER,'e80dd24b7cb7e18c97abb1effa705cbc2b7882b36ac8e439a181bc6cf3a6dfb1',219,13305313),
        (REVIEW,'00db7ec194949f945acb86d78e051873be7792076f05793e009ed9c7325739b5',42,3063531)]:
        assert row(folder/'seal.json')['sha256']==digest
        seal=json.loads((folder/'seal.json').read_bytes());members=seal['members']
        assert len(members)==seal['member_count']==count and sum(m['bytes'] for m in members)==seal['bytes']==total
        names={m['path'] for m in members};assert len(names)==count
        assert {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}==names|{'seal.json'}
        for p in folder.rglob('*'):
            assert not p.is_symlink()
            assert stat.S_IMODE(p.stat().st_mode)==(0o555 if p.is_dir() else 0o444)
        for m in members:
            rel=Path(m['path']);assert not rel.is_absolute() and '..' not in rel.parts
            raw=(folder/rel).read_bytes();assert len(raw)==m['bytes'] and sha(raw)==m['sha256']
        result.append({'path':str(folder.relative_to(ROOT)),'seal_sha256':digest,'members':count,'bytes':total})
    return result

assert not OUT.exists() and not ACCEPT.exists()
OUT.mkdir();before=custody()
program = '''import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import review_custody as c
current=c.snapshot()
old=c.load(c.HERE/'commands/fresh-independent-03/inputs-before.json')
guidance={'AGENTS.md','PLAN.md','mixer-product-plan.md'}
def priced(x):
    return {**x,'files':[r for r in x['files'] if r['path'] not in guidance]}
assert priced(current)==priced(old)
print(json.dumps({'success':True,'frozen_packets':current['complete_frozen_packets_checked'],'inherited_priced_inputs':current['inherited_priced_inputs'],'frozen_files':len(priced(current)['files']),'mutable_guidance_excluded_from_priced_custody':True,'snapshot_sha256':c.sha(c.canonical(priced(current)))}))
'''
env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','LANG':'C','LC_ALL':'C','TZ':'UTC','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0'}
argv=[sys.executable,'-B','-c',program,str(REVIEW)]
save(OUT/'plan.json',{'argv':argv,'environment':env,'cwd':str(ROOT),'timeout_seconds':45,
    'python':sys.version,'python_sha256':sha(Path(sys.executable).resolve().read_bytes()),
    'script':row(Path(__file__).resolve()),'review_custody_helper':row(REVIEW/'review_custody.py'),
    'custody_before':before,'source_revision':'d6af73813244c330a979afb83b45f53490ff5b29',
    'scope':'read-only complete frozen custody and retained final command evidence; no replay/compiler'})
start=time.monotonic();child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
timed=False
try: stdout,stderr=child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed=True;os.killpg(child.pid,signal.SIGTERM)
    try: stdout,stderr=child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid,signal.SIGKILL);stdout,stderr=child.communicate(timeout=5)
try: os.killpg(child.pid,0);absent=False
except ProcessLookupError: absent=True
for name,data in [('stdout',stdout),('stderr',stderr)]:
    with (OUT/name).open('xb') as f:f.write(data)
save(OUT/'receipt.json',{'argv':argv,'exit':child.returncode,'timed_out':timed,
    'elapsed_seconds':time.monotonic()-start,'owned_pid':child.pid,'owned_pgid':child.pid,
    'child_reaped':child.returncode is not None,'owned_group_absent':absent,
    'outputs':[row(OUT/n) for n in ['stdout','stderr']],'plan':row(OUT/'plan.json')})
assert child.returncode==0 and not timed and absent
checked=json.loads(stdout);assert checked['success'] and checked['frozen_packets']==18 and checked['inherited_priced_inputs']==1245
assert custody()==before
review=json.loads((REVIEW/'review.json').read_bytes())
assert row(REVIEW/'review.json')['sha256']=='7163df954a1b626821fd96303400cd0b15bcc4628f369aa6e38c97f8795bae3f'
assert review['status']=='recommend-bounded-partial-interface-acceptance'
checks=review['fresh_checks']
assert (checks['methods'],checks['failures'],checks['errors'],checks['adverse_cases_rejected'],checks['independent_equalities'])==(7,0,0,1473,532)
assert review['residuals']['count_per_unit']==30 and review['residuals']['work_and_storage_individually_positive']
final=json.loads((REVIEW/'commands/fresh-independent-03/receipt.json').read_bytes())
assert final['exit_code']==0 and final['waited_and_reaped'] and final['owned_group_absent'] and final['exact_frozen_inputs_before_after_unchanged']
for entry in [final['stdout'],final['stderr'],final['inputs_before'],final['inputs_after'],*final['source_programs']]:assert row(ROOT/entry['path'])==entry
assert b'Ran 7 tests' in (ROOT/final['stderr']['path']).read_bytes()
save(ACCEPT,{'schema':1,'at':datetime.now(timezone.utc).isoformat(),
    'status':'root-accepted-bounded-partial-provider-callee-source-interface',
    'custody':before,'root_check':row(OUT/'receipt.json'),'independent_review':row(REVIEW/'review.json'),
    'fresh_checks':checks,'findings_disposition':review['findings'],
    'known_shell_only':review['known_shell_only'],'mandatory_positive_residuals':review['residuals'],
    'preserved':review['preservation'],'historical_failures_preserved':review['history'],
    'conditional_closed_interfaces':10,'partial_interfaces':4,
    'all30_work_and_storage_contexts_required':True,
    'unobserved_u64_bool_aggregate_and_exact_callable_layouts_remain_unpriced':True,
    'complete_price_decrease_or_refund_selected':False,'root_policy_prices_funding_selected':False,
    'old_source_interface_binds_future_changed_Rust':False,
    'new_compiler_runtime_native_FieldLog_OTA_GA_acceptance':False})
print(json.dumps({'acceptance':row(ACCEPT),'fresh_methods':7,'mandatory_positive_contexts_each_unit':30}))
