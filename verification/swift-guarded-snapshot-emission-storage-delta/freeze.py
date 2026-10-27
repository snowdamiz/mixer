"""Bound the final pure control replay, then freeze only this owned packet."""
from pathlib import Path
import hashlib,json,os,signal,shutil,subprocess,sys,time
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def save(name,v):(HERE/name).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def manifest():
 return [{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['seal.json','freeze-receipt.json'] and '__pycache__' not in p.parts]
def main():
 if '--verify' in sys.argv:
  seal=json.loads((HERE/'seal.json').read_text());rows=manifest()
  assert rows==seal['members'] and sha(canonical(rows))==seal['members_tree_sha256']
  assert not (HERE/'owned-work').exists()
  print(json.dumps({'verified_members':len(rows),'seal_sha256':sha((HERE/'seal.json').read_bytes())}));return
 assert not (HERE/'seal.json').exists(),'frozen packet is immutable'
 assert not (HERE/'owned-work').exists()
 cache=HERE/'__pycache__'
 if cache.exists():shutil.rmtree(cache)
 argv=[sys.executable,str(HERE/'check.py'),'--verify'];env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'}
 (HERE/'final-control-check-source.py').write_bytes((HERE/'check.py').read_bytes())
 started=time.monotonic();p=subprocess.Popen(argv,cwd=HERE.parent.parent,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
 timed=False;actions=[]
 try:out,err=p.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True
  try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned control group')
  except ProcessLookupError:pass
  out,err=p.communicate()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 (HERE/'final-control.stdout').write_bytes(out);(HERE/'final-control.stderr').write_bytes(err)
 save('final-control-receipt.json',{'schema':1,'argv':argv,'python':sys.version,'python_executable':sys.executable,'platform':sys.platform,
  'check_source_sha256':sha((HERE/'check.py').read_bytes()),'source145_tree_sha256':json.loads((HERE/'source-manifest.json').read_text())['source_tree_sha256'],
  'exit_code':p.returncode,'timeout_seconds':55,'timed_out':timed,'elapsed_seconds':time.monotonic()-started,'owned_process_group':p.pid,'child_reaped':True,
  'owned_group_absent':absent,'cleanup_actions':actions,'stdout_sha256':sha(out),'stderr_sha256':sha(err),'scope':'pure Python integrity controls, nested read-only Git revision; no product/runtime/native execution'})
 assert p.returncode==0 and absent and not timed,(p.returncode,err.decode())
 rows=manifest();seal={'schema':1,'scope':'separable conditional helper storage/caller delta; compiler-only; no operational selection; owner base remains unaccepted',
  'member_count':len(rows),'member_bytes':sum(r['bytes'] for r in rows),'members_tree_sha256':sha(canonical(rows)),'source145_tree_sha256':json.loads((HERE/'source-manifest.json').read_text())['source_tree_sha256'],'members':rows}
 save('seal.json',seal);save('freeze-receipt.json',{'schema':1,'seal_sha256':sha((HERE/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':seal['member_bytes'],'all_children_reaped':True,'all_owned_groups_absent':True,'scratch_absent':True,'runtime_invocations':0,'owner_base_accepted':False})
 print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'member_count':len(rows),'member_bytes':seal['member_bytes']}))
if __name__=='__main__':main()
