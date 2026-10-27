#!/usr/bin/env python3
"""Run exactly one bounded pure Python checker and preserve its receipts."""
import datetime,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;R=D.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    require_target=sys.argv[1:];allowed={'derive.py','test_provenance.py','check.py','test_correction.py','custody.py','prepare_contracts.py','prepare_authored.py','test_adverse.py','test_exact_binding.py','audit.py','report.py','seal_check.py'}
    if not require_target or require_target[0] not in allowed:raise SystemExit('pure checker target required')
    require_not_frozen=not (D/'seal.json').exists()
    if not require_not_frozen:raise SystemExit('packet already frozen')
    logs=D/'commands';logs.mkdir(exist_ok=True);out=logs/f'attempt-{len(list(logs.glob("attempt-*")))+1:03d}';out.mkdir()
    scripts=[]
    for p in sorted(D.glob('*.py')):
        raw=p.read_bytes();scripts.append({'path':p.name,'bytes':len(raw),'sha256':sha(raw)});(out/('source-'+p.name)).write_bytes(raw)
    data_names=('candidate.json','graph.json','external-contracts.json','authored-contracts.json','typed-header-inventory.json','carrier-induction.json','input-bindings.json','caller-contract.json')
    def data_members():
        return {name:{'bytes':(D/name).stat().st_size,'sha256':sha((D/name).read_bytes())} for name in data_names if (D/name).exists()}
    def frozen_inventory():
        path=D/'input-bindings.json'
        if not path.exists():return None
        members={}
        for name,expected in json.loads(path.read_text())['files'].items():
            # This packet's preparation catalogs are mutable candidates, not
            # frozen inputs. Their before/after bytes are recorded separately.
            if name.startswith(str(D.relative_to(R))+'/'):continue
            raw=(R/name).read_bytes();actual={'bytes':len(raw),'sha256':sha(raw)}
            if actual!=expected:raise ValueError('pinned input changed:'+name)
            members[name]=actual
        return {'files':len(members),'inventory_sha256':sha(json.dumps(members,sort_keys=True,separators=(',',':')).encode())}
    before=data_members();frozen_before=frozen_inventory()
    argv=[sys.executable,'-B',str(D/require_target[0]),*require_target[1:]];started=time.monotonic()
    process=subprocess.Popen(argv,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",MIXER_STRING_PACKET_ACTIVE_ATTEMPT=str(out)))
    timed_out=False
    try:stdout,stderr=process.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed_out=True;os.killpg(process.pid,signal.SIGKILL);stdout,stderr=process.communicate()
        stderr+=b'\nonly this owned checker process group timed out, killed and waited\n'
    child=subprocess.CompletedProcess(argv,124 if timed_out else process.returncode,stdout,stderr)
    (out/'stdout').write_bytes(child.stdout);(out/'stderr').write_bytes(child.stderr)
    receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'argv':argv,'cwd':str(R),'python_version':sys.version,'python_executable_sha256':sha(Path(sys.executable).read_bytes()),'script_members':scripts,'script_tree_sha256':sha(json.dumps(scripts,sort_keys=True,separators=(',',':')).encode()),'source_revision':'frozen-source146-exacttree-690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185','exit_code':child.returncode,'elapsed_seconds':time.monotonic()-started,'stdout_sha256':sha(child.stdout),'stderr_sha256':sha(child.stderr),'owned_child_waited':True,'scope':'offline pinned source/typed compiler MIR data and pure checker tests only; no compiler/product/native/UI/capture/Git/root metadata/global process inventory','timeout_seconds':55,'PYTHONDONTWRITEBYTECODE':'1'}
    frozen_after=frozen_inventory()
    if frozen_before is not None and frozen_before!=frozen_after:raise ValueError('frozen input inventory changed')
    receipt.update({'data_members_before':before,'data_members_after':data_members(),'only_owned_packet_written':True,
        'frozen_inventory_before':frozen_before,'frozen_inventory_after':frozen_after,'owned_process_group':process.pid,'timeout_occurred':timed_out,'cleanup':'owned checker child waited; only its process group killed on timeout; no process inventory',
        'environment':{k:os.environ[k] for k in ('LANG','LC_ALL','LC_CTYPE','PYTHONHASHSEED') if k in os.environ},
        'MIXER_STRING_PACKET_ACTIVE_ATTEMPT':str(out),
        'compiler_or_product_execution':False,'native_or_UI_or_capture':False,'Git_or_global_inventory':False})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    sys.stdout.buffer.write(child.stdout);sys.stderr.buffer.write(child.stderr);raise SystemExit(child.returncode)
if __name__=='__main__':main()
