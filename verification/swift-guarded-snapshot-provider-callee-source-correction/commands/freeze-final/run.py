"""Bounded exact-own-group Python host runner; allowlisted scripts only."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
sys.dont_write_bytecode=True
from custody import roster,sha,row,HERE,ROOT

def main():
 label=sys.argv[1];tail=sys.argv[2:]
 if not label.replace('-','').isalnum() or not tail or tail[0] not in ('prepare.py','fetch.py','derive.py','test_correction.py','audit.py','freeze.py'):raise ValueError('bounded correction script allowlist')
 dest=HERE/'commands'/label;dest.mkdir(parents=True,exist_ok=False)
 before=roster();(dest/'inputs-before.json').write_text(json.dumps(before,sort_keys=True,indent=2)+'\n')
 scripts={p.name:row(p) for p in HERE.glob('*.py')}
 for p in HERE.glob('*.py'):(dest/p.name).write_bytes(p.read_bytes())
 argv=[sys.executable,'-B',str(HERE/tail[0]),*tail[1:]]
 env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0','LC_ALL':'C','LANG':'C'}
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
 child=subprocess.Popen(argv,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);timed=False
 try:out,err=child.communicate(timeout=55)
 except subprocess.TimeoutExpired:
  timed=True;os.killpg(child.pid,signal.SIGKILL);out,err=child.communicate(timeout=2)
 try:os.killpg(child.pid,0);absent=False
 except ProcessLookupError:absent=True
 (dest/'stdout').write_bytes(out);(dest/'stderr').write_bytes(err)
 after=roster();(dest/'inputs-after.json').write_text(json.dumps(after,sort_keys=True,indent=2)+'\n')
 unchanged=before==after;fetch_addition=tail==['fetch.py'] and all(x in after['files'] for x in before['files']) and before['frozen_packets']==after['frozen_packets'] and before['excluded_inherited_cache_metadata']==after['excluded_inherited_cache_metadata']
 receipt={'schema':1,'started':start,'elapsed_seconds':time.monotonic()-clock,'argv':argv,'cwd':str(ROOT),'environment':env,'tool_version':sys.version,'python_executable':str(Path(sys.executable).resolve()),'python_executable_sha256':sha(Path(sys.executable).resolve().read_bytes()),'source_scripts':scripts,'source_program_tree_sha256':sha(json.dumps(scripts,sort_keys=True,separators=(',',':')).encode()),'provider_source_tree_sha256':before['source_tree_sha256'],'frozen_input_custody_unchanged':unchanged or fetch_addition,'official_source_append_only_fetch':fetch_addition,'all_frozen_packet_membership_before_after_checked':True,'inputs_before':row(dest/'inputs-before.json'),'inputs_after':row(dest/'inputs-after.json'),'exit_code':child.returncode,'timed_out':timed,'timeout_seconds':55,'owned_PID':child.pid,'owned_PGID':child.pid,'owned_group_absent':absent,'child_reaped':child.poll() is not None,'stdout':row(dest/'stdout'),'stderr':row(dest/'stderr'),'compiler_product_native_runtime_UI_capture_phones_emulator_simulator_or_global_inventory':False,'scratch_created':False}
 (dest/'receipt.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'command':label,'exit_code':child.returncode,'seconds':receipt['elapsed_seconds'],'owned_group_absent':absent,'stdout':out.decode(errors='replace')[:3000],'stderr':err.decode(errors='replace')[-5000:]}))
 if child.returncode or timed or not absent or not(unchanged or fetch_addition):raise SystemExit(1)
 if tail==['freeze.py']:
  if (HERE/'seal.json').exists():raise ValueError('already immutable')
  members=[]
  for p in sorted(HERE.rglob('*')):
   if not p.is_file():continue
   if p.is_symlink() or '__pycache__' in p.parts:raise ValueError('foreign correction member')
   raw=p.read_bytes();members.append({'path':p.relative_to(HERE).as_posix(),'bytes':len(raw),'sha256':sha(raw)})
  seal={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Focused R1-R3 exact-source/type/count partial-frontier correction only; new independent review and root price selection required','members':members,'member_count':len(members),'bytes':sum(x['bytes'] for x in members),'all_command_receipts_closed_before_seal':True}
  (HERE/'seal.json').write_text(json.dumps(seal,sort_keys=True,indent=2)+'\n')
  print(json.dumps({'seal_sha256':sha((HERE/'seal.json').read_bytes()),'members':len(members),'bytes':seal['bytes']}))
if __name__=='__main__':main()
