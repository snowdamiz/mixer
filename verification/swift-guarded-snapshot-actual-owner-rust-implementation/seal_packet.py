"""Freeze/check this owned candidate without compiler/native execution."""
from pathlib import Path
import datetime,gzip,hashlib,json,os,sys
HERE=Path(__file__).resolve().parent

def sha(b):return hashlib.sha256(b).hexdigest()
def digest(j):return sha(json.dumps(j,sort_keys=True,separators=(',',':')).encode())
def row(p):
 raw=p.read_bytes();return dict(path=str(p.relative_to(HERE)),bytes=len(raw),sha256=sha(raw))
def write(p,j):p.write_text(json.dumps(j,sort_keys=True,indent=2)+'\n')
def check():
 seal=json.loads((HERE/'seal.json').read_bytes());actual=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p!=HERE/'seal.json']
 assert actual==seal['members'] and digest(actual)==seal['tree_sha256'] and sum(r['bytes'] for r in actual)==seal['member_bytes']
 assert not (HERE/'build').exists()
 return dict(seal_sha256=sha((HERE/'seal.json').read_bytes()),members=len(actual),bytes=seal['member_bytes'],tree_sha256=seal['tree_sha256'])
if __name__=='__main__':
 if sys.argv[1:]==['--check']:print(json.dumps(check(),sort_keys=True));raise SystemExit()
 assert sys.argv[1:]==['--freeze'] and not (HERE/'seal.json').exists()
 import run_bounded
 before=run_bounded.frozen()
 source=json.loads((HERE/'final-source-manifest.json').read_text());assert source['member_count']==146
 for expected in source['members']:
  p=HERE/'source/vm'/expected['path'];raw=p.read_bytes();assert len(raw)==expected['bytes'] and sha(raw)==expected['sha256']
 retention=json.loads((HERE/'artifact-retention.json').read_text());raw=gzip.decompress((HERE/retention['full_MIR_archive']['path']).read_bytes())
 assert sha(raw)==retention['full_MIR_raw_sha256'] and len(raw)==retention['full_MIR_raw_bytes']
 inventory=json.loads((HERE/'mir-inventory.json').read_text());assert sha(raw)==inventory['input']['sha256'] and inventory['complete_item_count']==6207
 commands=[]
 for p in sorted((HERE/'commands').glob('*/plan.json')):
  j=json.loads(p.read_text());r=json.loads((p.parent/'receipt.json').read_text());assert r['child_reaped'] and r['exact_owned_group_absent'] and r['input_unchanged'] and r['source_unchanged'] and r['output_within_caps'] and r['elapsed_seconds']<55
  try:os.killpg(r['owned_pgid'],0);absent=False
  except ProcessLookupError:absent=True
  assert absent
  commands.append(dict(command=p.parent.name,kind=j['kind'],exit=r['exit'],at=j['at'],seconds=r['elapsed_seconds'],owned_pid=r['owned_pid'],owned_pgid=r['owned_pgid'],reaped=True,group_absent=True))
 assert sum(c['kind']=='compiler' for c in commands)==16 and sum(c['kind']=='host' for c in commands)==5
 # No owned compiler time intervals overlap. Host and audit runs are separately
 # attributed; no broad/genuine-loader execution exists in this command roster.
 compiler=sorted((c for c in commands if c['kind']=='compiler'),key=lambda c:c['at'])
 for a,b in zip(compiler,compiler[1:]):
  at=datetime.datetime.fromisoformat(a['at']);bt=datetime.datetime.fromisoformat(b['at']);assert (bt-at).total_seconds()>a['seconds']
 for mode in ['debug','opt']:
  stdout=(HERE/'commands'/('run-'+mode+'-proof-error')/'stdout').read_text();assert '15 passed; 0 failed' in stdout
 for n in range(1,9):
  base=HERE/'probes'/f'N{n:02d}';result=json.loads((base/'result.json').read_text());assert result['compiler_refused'] and result['diagnostics_found'] and not result['rmeta_created']
  if n!=5:assert result['intended_names_found']
  else:assert json.loads((base/'result-review.json').read_text())['diagnostic']=='E0423'
 after=run_bounded.frozen();assert before==after
 write(HERE/'final-custody.json',dict(before=before,after=after,unchanged=True,count=len(before),tree_sha256=digest(before),scope='final direct packets, all479 inherited custody paths,146 origins,host11,root selections/amendments'))
 write(HERE/'command-summary.json',dict(commands=commands,compiler_invocations=16,host_runs=5,compiler_ceiling=16,host_ceiling=5,layout_queries=0,compiler_intervals_disjoint=True,all_owned_children_reaped=True,all_exact_owned_groups_absent=True,native_fixture_UI_runtime=False,acceptance=False))
 write(HERE/'cleanup.json',dict(command_children=len(commands),all_reaped=True,all_exact_owned_groups_absent=True,owned_build_scratch_absent=True,full_MIR_retained=True,raw_or_native_owner_tests_run=False,global_inventory=False,foreign_processes_touched=False,source_and_host_retained=True))
 write(HERE/'preparation.json',dict(reads='AGENTS,binding plan/PLAN,complete frozen selection/source map/host plan,actual146 origin contracts,complete referenced ownership model/interface/contract,actual loader/proof/caller/account source',memory='targeted registry search had no relevant fact and supplied no evidence or test source',nonqualifying_preparation='source navigation,script/source authoring and reconstruction; initial expected missing-path reads are retained in conversation, not test/compile failures',original_failures='original Debug target span fixture error; N05 overstrict diagnostic checker; three offline MIR parser/display checks',first_two_audit_preimages='reconstructed from exact one-line parser/display correction; final audit script inputs captured contemporaneously',no_production_authority=True,no_canonical_or_other_lane_edit=True,no_Git_dependency_native_UI=True))
 members=[row(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p!=HERE/'seal.json']
 seal=dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),member_count=len(members),member_bytes=sum(r['bytes'] for r in members),members=members,tree_sha256=digest(members),source146_tree=source['tree_sha256'],compiler_invocations=16,filtered_host_runs=5,final_host_methods_per_mode=15,full_MIR_items=6207,scope='unaccepted isolated Rust source/compiler/host-component candidate only',root_acceptance=False,native_bridge_policy_funding_File_healthy_close_FieldLog_OTA_GA='pending',all17fields_8claims_3Pendingselectors_6Pendingupstream_6childcomponents_preserved=True)
 write(HERE/'seal.json',seal)
 for p in HERE.rglob('*'):
  if p.is_file():p.chmod(p.stat().st_mode&~0o222)
 print(json.dumps(check(),sort_keys=True))
