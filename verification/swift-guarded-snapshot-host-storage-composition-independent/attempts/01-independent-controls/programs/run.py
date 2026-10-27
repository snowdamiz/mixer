"""Run independent data review and hostile tests, retaining all attempts."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, sys, time
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def run_child(argv,label,attempt):
    before=time.monotonic();at=datetime.datetime.now(datetime.timezone.utc).isoformat()
    proc=subprocess.run(argv,cwd=ROOT,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    path=attempt/label;path.mkdir()
    (path/'stdout').write_bytes(proc.stdout);(path/'stderr').write_bytes(proc.stderr)
    executable=Path(sys.executable).resolve()
    receipt={'schema':1,'argv':argv,'cwd':str(ROOT),'at':at,'elapsed_seconds':time.monotonic()-before,
      'python_version':sys.version,'python_executable':str(executable),'python_executable_sha256':sha(executable.read_bytes()),
      'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185',
      'host_tree_sha256':'027394c31852db7845a3162115e7bcd8b5f9a5044cbb495910c5c03c4fb20de2',
      'source_revision_binding':'root-supplied historical source acceptance revision510c2e123b356de6fda062379e6cbaa2233e69e3; no live Git read',
      'own_program_preimages':[{'path':str(p.relative_to(HERE)),'sha256':sha(p.read_bytes()),'bytes':len(p.read_bytes())} for p in sorted(HERE.glob('*.py'))],
      'exit_code':proc.returncode,'direct_child_waited':True,'timeout_seconds':60,
      'stdout_sha256':sha(proc.stdout),'stderr_sha256':sha(proc.stderr),
      'compiler_product_native_simulator_UI_capture_global_process_inventory':False}
    save(path/'receipt.json',receipt)
    return proc
def main():
    assert not (HERE/'seal.json').exists(),'frozen: use verify.py'
    attempts=HERE/'attempts';attempts.mkdir(exist_ok=True)
    number=len(list(attempts.iterdir()))+1;attempt=attempts/f'{number:02d}-independent-controls';attempt.mkdir()
    sources=attempt/'programs';sources.mkdir()
    for p in HERE.glob('*.py'):shutil.copyfile(p,sources/p.name)
    audit=run_child([sys.executable,'-B',str(HERE/'audit.py')],'audit',attempt)
    hostile=run_child([sys.executable,'-B','-m','unittest','discover','-s',str(HERE),'-p','hostile_controls.py','-v'],'hostile',attempt)
    summary={'schema':1,'latest_attempt':str(attempt.relative_to(HERE)),'audit_exit':audit.returncode,'hostile_exit':hostile.returncode,
             'all_passed':audit.returncode==0 and hostile.returncode==0,
             'attempts':[str(p.relative_to(HERE)) for p in sorted(attempts.iterdir())]}
    save(HERE/'attempt-history.json',summary)
    if summary['all_passed']:
        save(HERE/'audit-results.json',json.loads(audit.stdout))
        save(HERE/'results.json',{'schema':1,'all_passed':True,'independent_hostile_methods':20,
             'conditional_storage_interface_reviewed':True,'synthetic_positive_cuts_qualify_actual_fixture':False,
             'root_policy_whole_quote_native_or_GA':False,'source_tree_sha256':'690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185'})
    print(json.dumps(summary,sort_keys=True))
    return 0 if summary['all_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
