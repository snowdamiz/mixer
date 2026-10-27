#!/usr/bin/env python3
"""Seal the independent review once; --check-only is read-only."""
import datetime,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def members():
    result=[]
    for p in sorted(D.rglob('*')):
        if p.is_file() and p!=D/'seal.json':
            assert not p.is_symlink();b=p.read_bytes();result.append({'path':str(p.relative_to(D)),'bytes':len(b),'sha256':sha(b)})
    return result
if '--check-only' not in sys.argv:
    assert not (D/'seal.json').exists()
    receipts=[]
    for p in sorted((D/'commands').glob('*/receipt.json')):
        r=json.loads(p.read_text());assert r['child_reaped'] and r['owned_group_absent'] and not r['timed_out']
        receipts.append({'path':str(p.parent.relative_to(D)),'exit_code':r['exit_code'],'expectation_met':r['expectation_met'],'source_revision':r['source_revision_at_command'],'elapsed_seconds':r['elapsed_seconds']})
    failures=[r for r in receipts if not r['expectation_met']]
    assert len(failures)==1 and failures[0]['path']=='commands/attempt01-independent-source-audit'
    (D/'attempt-history.json').write_text(json.dumps({'schema':1,'attempts':receipts,'checker_failures_retained':1,'failure_cause':'independent scanner initially omitted PrepaidOwnedV1<T> concrete substitution; actual entry and destructor signatures now bind it','frozen_input_mutations':0},indent=2,sort_keys=True)+'\n')
    (D/'cleanup.json').write_text(json.dumps({'schema':1,'all_direct_python_children_waited':True,'owned_groups_absent':True,'new_compiler_product_fixture_native_UI_capture_started':False,'native_runtime':'paused','global_process_inventory':False,'owned_runtime_scratch_created':0,'other_projects_touched':False,'Git_mutations':False},indent=2,sort_keys=True)+'\n')
    (D/'freeze-command.json').write_text(json.dumps({'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':['python3','-B',str(D/'freeze.py')],'cwd':str(D.parents[1]),'python_version':sys.version,'script_sha256':sha(Path(__file__).read_bytes()),'source146_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','scope':'independent source/interface component plus read-only retained-IR partial correspondence review'},indent=2,sort_keys=True)+'\n')
    roster=members();s={'schema':1,'status':'frozen-independent-source-interface-review-no-required-source-correction-partial-IR-correspondence','member_count':len(roster),'member_bytes':sum(m['bytes'] for m in roster),'tree_sha256':sha(json.dumps(roster,sort_keys=True,separators=(',',':')).encode()),'members':roster,'source_controls':23347,'IR_controls':4221,'compiled_std_correspondence_complete':False,'whole_host_grant_or_GA':False,'native_runtime':'paused'}
    (D/'seal.json').write_text(json.dumps(s,indent=2,sort_keys=True)+'\n')
else:
    s=json.loads((D/'seal.json').read_text());roster=members();assert roster==s['members'] and len(roster)==s['member_count'] and sum(m['bytes'] for m in roster)==s['member_bytes'] and sha(json.dumps(roster,sort_keys=True,separators=(',',':')).encode())==s['tree_sha256']
print(json.dumps({'status':'verified' if '--check-only' in sys.argv else 'sealed','members':s['member_count'],'bytes':s['member_bytes'],'seal_sha256':sha((D/'seal.json').read_bytes())},sort_keys=True))
