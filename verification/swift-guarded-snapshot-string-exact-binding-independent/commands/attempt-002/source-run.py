"""Bound one pure host child group; retain exact scripts, inputs and outputs."""
import datetime,json,os,signal,subprocess,sys,time
from common import D,R,C,SOURCE,HOST,sha,encoded,inventory,need
def main():
 need(not (D/'seal.json').exists(),'review frozen');args=sys.argv[1:]
 need(args and args[0] in ('audit.py','adverse.py','custody.py','producer'),'bounded review target')
 argv=[sys.executable,'-B',str((C if args[0]=='producer' else D)/(args[1] if args[0]=='producer' else args[0])),*(args[2:] if args[0]=='producer' else args[1:])]
 if args[0]=='producer':need(args[1:] in [['test_adverse.py'],['seal_check.py'],['check.py'],['prepare_authored.py','--check'],['prepare_contracts.py','--check'],['custody.py','--check'],['audit.py','--check']],'read-only producer target')
 logs=D/'commands';logs.mkdir(exist_ok=True);out=logs/f'attempt-{len(list(logs.glob("attempt-*")))+1:03d}';out.mkdir()
 scripts={p.name:{'bytes':len(p.read_bytes()),'sha256':sha(p.read_bytes())} for p in sorted(D.glob('*.py'))}
 for name in scripts:(out/('source-'+name)).write_bytes((D/name).read_bytes())
 before=inventory();(out/'inputs-before.json').write_bytes(encoded(before));start=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
 child=subprocess.Popen(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 timeout=False
 try:stdout,stderr=child.communicate(timeout=55)
 except subprocess.TimeoutExpired:timeout=True;os.killpg(child.pid,signal.SIGKILL);stdout,stderr=child.communicate()
 after=inventory();(out/'inputs-after.json').write_bytes(encoded(after));(out/'stdout').write_bytes(stdout);(out/'stderr').write_bytes(stderr)
 receipt={'schema':1,'at':at,'argv':argv,'cwd':str(R),'python_version':sys.version,'python_executable':sys.executable,'python_executable_sha256':sha(__import__('pathlib').Path(sys.executable).read_bytes()),'review_scripts':scripts,'source_tree_sha256':SOURCE,'host_tree_sha256':HOST,'inputs_before_sha256':sha(encoded(before)),'inputs_after_sha256':sha(encoded(after)),'inputs_unchanged':before==after,'input_count':len(before),'stdout_sha256':sha(stdout),'stderr_sha256':sha(stderr),'exit_code':124 if timeout else child.returncode,'elapsed_seconds':time.monotonic()-start,'timeout_seconds':55,'timeout_occurred':timeout,'owned_process_group':child.pid,'owned_child_waited':True,'owned_cleanup':'child group waited; only owned group killed if deadline exceeded; no process inventory','native_or_UI_or_capture':False,'compiler_or_product_execution':False,'Git_or_global_inventory':False,'environment':{'PYTHONDONTWRITEBYTECODE':'1',**{k:os.environ[k] for k in ('LANG','LC_ALL','LC_CTYPE','PYTHONHASHSEED') if k in os.environ}}}
 (out/'receipt.json').write_bytes(encoded(receipt));sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr);need(before==after,'frozen input mutation');raise SystemExit(receipt['exit_code'])
if __name__=='__main__':main()
