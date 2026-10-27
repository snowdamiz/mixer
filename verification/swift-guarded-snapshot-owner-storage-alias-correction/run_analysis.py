"""Capture bounded source-analysis commands and their exact tool/input custody."""
from pathlib import Path
import json,os,signal,subprocess,sys,time
from correct import ROOT,PRODUCER,PREACCESS,sha,canonical,custody

def command(label,argv):
    outdir=ROOT/'commands'/label;outdir.mkdir(parents=True,exist_ok=False)
    binding=custody();started=time.monotonic()
    p=subprocess.Popen(argv,cwd=ROOT.parent.parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed=False;actions=[]
    try:out,err=p.communicate(timeout=55)
    except subprocess.TimeoutExpired:
        timed=True
        try:os.killpg(p.pid,signal.SIGKILL);actions.append('SIGKILL owned group')
        except ProcessLookupError:pass
        out,err=p.communicate()
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    (outdir/'stdout').write_bytes(out);(outdir/'stderr').write_bytes(err)
    receipt={'schema':1,'argv':argv,'exit_code':p.returncode,'python_version':sys.version,
             'python_executable':sys.executable,'driver_sha256':sha(Path(argv[1]).read_bytes()),
             'source_binding':binding,'elapsed_seconds':time.monotonic()-started,
             'timeout_seconds':55,'timed_out':timed,'owned_process_group':p.pid,
             'new_session':True,'child_reaped':True,'owned_group_absent':absent,
             'cleanup_actions':actions,'stdout_sha256':sha(out),'stderr_sha256':sha(err),
             'source_revision_scope':'exact immutable producer and accepted source-tree seals; no mutable repository tree is claimed',
             'scope':'Python source/MIR/recipe integrity analysis only; no native or engine runtime, process inventory or Git mutation'}
    (outdir/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    assert not timed and absent and p.returncode==0,(label,err.decode())
    print(label+': '+out.decode().strip(),flush=True)
    custody()

if __name__=='__main__':
    prefix=sys.argv[1] if len(sys.argv)>1 else 'replay'
    for name in ['correct','calls','check','adversarial']:
        command(prefix+'-'+name,[sys.executable,str(ROOT/(name+'.py'))])
