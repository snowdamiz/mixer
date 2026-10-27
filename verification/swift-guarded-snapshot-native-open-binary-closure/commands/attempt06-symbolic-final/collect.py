"""One root-authorized, bounded installed-library disassembly; no compilation."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

sys.dont_write_bytecode = True
D = Path(__file__).resolve().parent
R = D.parents[1]
B = R / 'verification/swift-guarded-snapshot-resource-binary-correspondence'
PINNED = {
    'swift-guarded-snapshot-resource-binary-correspondence': '58f49d3bcc844678bef604bc4989e81b2bfea758b300ca3158b229a510018f1d',
    'swift-guarded-snapshot-resource-binary-independent': '84976ed430d7ec841875e9422a5673d8746ae105e4efbb864cd443debf8792c7',
    'swift-guarded-snapshot-native-interface-bounds': 'd02b6602bc7c4419d908db90a8e67d24b1dd3a46f9c9d2c2bb9158c70229b60f',
    'swift-guarded-snapshot-native-interface-independent': '529bfac197ef63810ba4d00a1814426be9fb23392e5062c1189c898a7ffd2ea5',
}
SYMBOLS = [
    '__RNvMsj_NtCs1SSuMAdGM58_3std2fsNtB5_11OpenOptions5__open',
    '__RNvXs_NvMs_NtNtCs6zY7rJBZy9D_5alloc3ffi5c_strNtB9_7CString3newRShNtB4_11SpecNewImpl13spec_new_impl',
    '__RNvMs3_NtNtCsjIpoRzUjyHQ_4core3ffi5c_strNtB5_4CStr19from_bytes_with_nul',
]

def sha(b): return hashlib.sha256(b).hexdigest()
def put(name, data): (D/name).write_text(json.dumps(data, indent=2, sort_keys=True)+'\n')
def checked(p, row):
    b=p.read_bytes()
    assert len(b)==row['bytes'] and sha(b)==row['sha256'],str(p)
    return b

def main():
    assert not (D/'disassembly-receipt.json').exists(), 'single query already recorded'
    bindings=[]
    for name,h in PINNED.items():
        p=R/'verification'/name
        sb=(p/'seal.json').read_bytes(); assert sha(sb)==h
        seal=json.loads(sb)
        for row in seal['members']: checked(p/row['path'],row)
        bindings.append(dict(path=str(p.relative_to(R)),seal_sha256=h,members=len(seal['members'])))
    installed=json.loads((B/'installed-inputs.json').read_text())
    compatible=json.loads((B/'compatible-installed-tools.json').read_text())
    tool=compatible['tools']['llvm-objdump']; checked(Path(tool['path']),tool)
    checked(Path(compatible['libLLVM']['path']),compatible['libLLVM'])
    archives=[installed['archives'][x] for x in ('std','alloc','core')]
    for row in archives: checked(Path(row['path']),row)
    argv=[tool['path'],'--disassemble-symbols='+','.join(SYMBOLS),'--reloc',*[x['path'] for x in archives]]
    plan=dict(authorization='Root message approved exactly three selected symbols after compiler slot release; one supported invocation, up to three sequential calls only for tool-interface refusal.',
      symbols=SYMBOLS,argv=argv,timeout_seconds=15,tool=tool,libLLVM=compatible['libLLVM'],archives=archives,
      frozen_inputs=bindings,compiler=False,product_runtime=False,global_process_inventory=False)
    put('disassembly-plan.json',plan)
    env={'LC_ALL':'C','PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'}
    start=time.monotonic(); actions=[]; timed_out=False
    child=subprocess.Popen(argv,cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try: out,err=child.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        timed_out=True;os.killpg(child.pid,signal.SIGKILL);actions.append('SIGKILL owned process group after15s');out,err=child.communicate()
    try: os.killpg(child.pid,0);absent=False
    except ProcessLookupError: absent=True
    outputs={}
    for name,b in [('stdout',out),('stderr',err)]:
        archive='disassembly.'+name+'.gz'; (D/archive).write_bytes(gzip.compress(b,mtime=0))
        outputs[name]=dict(archive=archive,bytes=len(b),sha256=sha(b))
    put('disassembly-receipt.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),argv=argv,cwd=str(R),environment=env,
      direct_child_pid=child.pid,direct_child_waited=True,elapsed_seconds=time.monotonic()-start,exit_code=child.returncode,
      timeout_seconds=15,timed_out=timed_out,owned_group_absent=absent,cleanup_actions=actions,outputs=outputs,
      compiler=False,product_runtime=False,global_process_inventory=False))
    assert child.returncode==0 and not timed_out and absent
    print(json.dumps(dict(exit_code=child.returncode,stdout_bytes=len(out),stderr_bytes=len(err),owned_group_absent=absent)))

if __name__=='__main__': main()
