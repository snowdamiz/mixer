#!/usr/bin/env python3
"""Freeze a separate runner-only revision; preserve source/probe/original bytes."""
from pathlib import Path
import datetime,hashlib,json,sys
P=Path(__file__).resolve().parent;R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def row(path,base=P):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def write_once(path,value):
    with path.open('x') as output:json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
originals={'run_bounded.py':'1d60afac925840008549874c9fd23c3e56aee894d63631584de4750b3c464520',
 'proposed-command-roster.json':'6d5c05a76906015675e1e646d212577f429b4732780b2cee1ab422a7385f4006',
 'source-freeze.json':'93ac93f9dbea57db26d5b58301981c26f1d25d190a565cac46574fa7436eaca8'}
for name,digest in originals.items():assert sha((P/name).read_bytes())==digest,name
original=json.loads((P/'source-freeze.json').read_text())
for member in original['members']:assert row(P/member['path'])==member,member['path']
assert original['source146_tree']=='91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f'
assert original['host11_tree']=='027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2'
roster=json.loads((P/'proposed-command-roster.json').read_text())
roster['schema']=2
roster['status']='immutable-runner-only-v2-awaiting-root-review-and-compiler-release'
roster['preserved_original_roster']=row(P/'proposed-command-roster.json',R)
roster['runner']=row(P/'run_bounded_v2.py',R)
roster['cleanup_and_capture']={'outer_finally':True,'exact_owned_PID_PGID_only':True,'write_once_receipts':True,
 'fixed_failure_classification':True,'nonblocking_pipe_captured_prefix_each_max':4194304,'work_deadline_seconds':51,
 'cleanup_deadline_seconds':54.5,'total_seconds_max':55,'failure_injection_execution':False}
assert roster['commands']==json.loads((P/'proposed-command-roster.json').read_text())['commands']
write_once(P/'proposed-command-roster-v2.json',roster)
paths=[P/member['path'] for member in original['members']]
paths += [P/'source-freeze.json',P/'run_bounded_v2.py',P/'proposed-command-roster-v2.json',P/'runner-v2-review.md',P/'prepare_runner_v2.py']
write_once(P/'source-freeze-v2.json',{'schema':2,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,
 'status':'runner-only-v2-immutable-source-proposal-no-compiler-or-host-execution','source146_tree':original['source146_tree'],
 'host11_tree':original['host11_tree'],'preserved_original_freeze':row(P/'source-freeze.json'),
 'members':[row(path) for path in sorted(set(paths))],'source_members_pinned_indirectly_by_manifests':True,
 'source_probe_and_original_runner_roster_freeze_unchanged':True,'compiler_host_version_commands_executed':0})
print(json.dumps({'runner_v2':row(P/'run_bounded_v2.py'),'roster_v2':row(P/'proposed-command-roster-v2.json'),'freeze_v2':row(P/'source-freeze-v2.json'),
 'unchanged_source146_tree':original['source146_tree'],'unchanged_host11_tree':original['host11_tree']}))
