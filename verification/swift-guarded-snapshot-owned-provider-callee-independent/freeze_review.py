"""Freeze only this independent review directory, with no child process."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import run_review

OWN=Path(__file__).resolve().parent
ROOT=OWN.parents[1]

def sha(body):return hashlib.sha256(body).hexdigest()
def write(name,value): (OWN/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def main():
    start=time.monotonic()
    assert not (OWN/'seal.json').exists()
    before=run_review.custody()
    assert before['ok']
    commands=[];failed=[]
    for path in sorted((OWN/'commands').glob('*/receipt.json')):
        r=json.loads(path.read_text())
        if r['child_spawned']:
            assert r['exit_code']==0 and not r['timed_out'] and r['postflight_ok'] and r['same_custody_before_after'] and r['owned_process_group_absent_after_reap']
            commands.append({'command':path.parent.name,'pid':r['child_pid'],'pgid':r['child_pgid'],'waited_exit':r['exit_code'],'owned_group_observed_absent_after_reap':True})
        else:
            assert path.parent.name in ('source-trace-01','complete-preimages-01')
            failed.append({'command':path.parent.name,'child_spawned':False,'receipt_sha256':sha(path.read_bytes())})
        for s in r['source_files']:
            p=path.parent/'source-programs'/Path(s['path']).name
            assert p.stat().st_size==s['bytes'] and sha(p.read_bytes())==s['sha256']
    assert len(failed)==2
    after=run_review.custody()
    assert after==before and after['ok']
    write('final-input-custody.json',after)
    write('cleanup.json',{'schema':1,'all_owned_children':commands,'all_owned_children_reaped_and_groups_observed_absent':True,
          'preflight_no_spawn':failed,'new_runtime_or_capture_instances_started':False,'scratch_instances_to_shutdown':0,
          'global_process_inventory':False,'other_project_processes_touched':False,
          'compiler_queries_or_product_native_UI_runtime':False,'frozen_or_unrelated_cache_touched':False})
    write('attempt-history.json',{'schema':1,'reviewer_failures_preserved':failed,
          'source-trace-01':'Reviewer excluded listed freeze-receipt.json as an envelope file; no digest mismatch and no child spawn; fixed only own membership rule.',
          'complete-preimages-01':'Reviewer initially applied a stricter inherited membership rule than frozen producer derive.py:31. Exact unpriced cache metadata is retained separately by final custody; no priced input changed; no child spawn.',
          'producer_failures':'Unmodified inside exact230-member frozen candidate, including both mutable-PLAN child-free preflight failures.',
          'original_live_PLAN_bytes_recovered':False,'live_PLAN_is_priced_input':False,
          'historical_reviewer_programs_retained_and_digest_verified':True})
    programs=[run_review.digest(p) for p in sorted(OWN.glob('*.py'))]
    elapsed=time.monotonic()-start
    assert elapsed<55
    write('freeze-receipt.json',{'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'argv':sys.argv,'cwd':str(ROOT),'python':sys.version,'executable':run_review.digest(Path(sys.executable)),
          'env':{k:os.environ.get(k) for k in ('PATH','LANG','LC_ALL','PYTHONDONTWRITEBYTECODE')},
          'source_files':programs,'source_tree_sha256':sha(json.dumps(programs,sort_keys=True,separators=(',',':')).encode()),
          'pid':os.getpid(),'pgid':os.getpgid(0),'child_spawned':False,'exit_code':0,'bounded_seconds':55,'elapsed_seconds':elapsed,
          'input_members':1245,'frozen_complete_packets':15,'candidate_members':230,
          'before_after_custody_equal':before==after,'custody_sha256':sha((OWN/'final-input-custody.json').read_bytes()),
          'scope':'Freeze independent correction review only; all omissions and pending qualification preserved.'})
    members=[]
    for path in sorted(OWN.rglob('*')):
        assert not path.is_symlink()
        if path.is_file():
            assert '__pycache__' not in path.parts
            b=path.read_bytes();members.append({'path':str(path.relative_to(OWN)),'bytes':len(b),'sha256':sha(b)})
    write('seal.json',{'schema':1,'status':'independent-source-closure-correction-required',
          'candidate_seal_sha256':'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0',
          'source_tree_sha256':'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d',
          'members':members,'member_count':len(members),'total_bytes':sum(x['bytes'] for x in members),
          'root_price_funding_OTA_GA_acceptance':False})
    print(json.dumps({'seal_sha256':sha((OWN/'seal.json').read_bytes()),'members':len(members),'bytes':sum(x['bytes'] for x in members),'findings':3,'status':'focused-source-correction-required'}))

if __name__=='__main__':main()
