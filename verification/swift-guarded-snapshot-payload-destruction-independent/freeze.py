"""Freeze or read-only verify this bounded independent packet."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent
def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def roster():
 out=[]
 for p in sorted(D.rglob('*')):
  if p.is_file() and p.name!='seal.json':
   assert not p.is_symlink()
   data=p.read_bytes();out.append(dict(path=str(p.relative_to(D)),bytes=len(data),sha256=sha(data)))
 return out
if '--check-only' not in sys.argv:
 assert not (D/'seal.json').exists()
 attempts=[]
 for p in sorted((D/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());assert r['direct_child_waited'] and r['owned_group_absent'] and not r['timed_out']
  attempts.append(dict(path=str(p.parent.relative_to(D)),exit_code=r['exit_code'],review_sha256=r['review_sha256'],elapsed_seconds=r['elapsed_seconds']))
 corrections={
  'attempt01-independent-source-graph':'Independent type parser lacked unsized slice spelling behind Box; added a slice AST frontier spelling.',
  'attempt02-unsized-frontier-spelling':'Independent algebra did not substitute generic arguments inside Vec<T>; added recursive AST substitution.',
  'attempt03-nested-generic-substitution':'Independent diagnostic parser treated the retained unused-import warning as an error; filter errors explicitly.',
  'attempt04-error-diagnostic-filter':'Expected array size is spelled usize::MAX in the primary label; check that exact symbolic expected value.',
  'attempt05-symbolic-expected-array-size':'MIR local declarations retained spaces before comments; strip before matching local type declarations.',
  'attempt07-inherited-layout-and-mutation-controls':'Historical actual90 query explicitly prefixes lib.rs with never_type for its ! query; reconcile the unchanged-body prefix.'
 }
 for attempt in attempts:
  attempt['checker_only_failure_correction']=corrections.get(Path(attempt['path']).name)
 (D/'attempt-history.json').write_text(json.dumps(dict(schema=1,attempts=attempts,failed_checker_attempts=sum(a['exit_code']!=0 for a in attempts),frozen_input_or_product_corrections=0),indent=2,sort_keys=True)+'\n')
 record=dict(argv=['python3','-B',str(D/'freeze.py')],cwd=str(D.parents[1]),python_version=sys.version,script_sha256=sha(Path(__file__).read_bytes()),source_tree_sha256='690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',output='seal.json',product_or_compiler_executed=False,status='sealed')
 (D/'freeze-command.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
 members=roster()
 result=dict(schema=1,scope='independent bounded conditional payload interface; thirteen layout observations closed; no resource costs selected or grant',members=members,member_count=len(members),member_bytes=sum(m['bytes'] for m in members),tree_sha256=sha(canonical(members)))
 (D/'seal.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
else:
 result=json.loads((D/'seal.json').read_text());members=roster()
 assert members==result['members']
 assert len(members)==result['member_count'] and sum(m['bytes'] for m in members)==result['member_bytes']
 assert sha(canonical(members))==result['tree_sha256']
print(json.dumps(dict(status='verified' if '--check-only' in sys.argv else 'sealed',members=result['member_count'],bytes=result['member_bytes'],seal_sha256=sha((D/'seal.json').read_bytes())),sort_keys=True))
