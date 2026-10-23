#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,subprocess,time
HERE=Path(__file__).resolve().parent
TREE=HERE/'tree'
def sha(b):return hashlib.sha256(b).hexdigest()
env=os.environ|{'PATH':'/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],'CARGO_TARGET_DIR':str(HERE/'build'),'TMPDIR':str(HERE/'tmp')}
inclusions={'vm/src/experimental_swift_reactor/cache.rs':'cache_probe_inspection.rs',
            'vm/src/experimental_swift_reactor/control.rs':'control_probe_inspection.rs',
            'vm/src/experimental_wasi/accounted.rs':'wasi_probe_inspection.rs',
            'vm/src/experimental_swift_reactor/cache_tests.rs':'independent_probes.rs'}
baseline=json.loads((HERE/'full-vm-input-manifest.json').read_text())
overlays={}
for target,probe in inclusions.items():
    path=TREE/target
    data=path.read_bytes()
    expected=baseline[target]
    addition=('\n#[cfg(test)]\ninclude!('+json.dumps(str(HERE/probe))+');\n').encode()
    if sha(data)==expected:path.write_bytes(data+addition)
    else:assert data.endswith(addition),target
    overlays[target]={'frozen_sha256':expected,'derived_sha256':sha(path.read_bytes()),'test_include':probe,'test_include_sha256':sha((HERE/probe).read_bytes())}
commands=[]
for mode in ['debug','release']:
    argv=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--all-features','--lib']
    if mode=='release':argv+=['--release']
    argv+=['experimental_swift_reactor::cache_tests::independent_','--','--nocapture','--test-threads=1']
    start=time.monotonic();p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True)
    output=p.stdout+p.stderr
    passed=sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',output)))
    log=f'independent-probes-{mode}.log';(HERE/log).write_text(output)
    commands.append({'argv':argv,'cwd':str(TREE),'exit_code':p.returncode,'seconds':time.monotonic()-start,'passed':passed,'output':log,'output_sha256':sha(output.encode())})
    (HERE/'independent-probes.json').write_text(json.dumps({'scope':'test-only isolated copies; candidate2 product source immutable','overlays':overlays,'commands':commands},indent=2)+'\n')
    print(f'{mode} exit={p.returncode} passed={passed}\n{output[-7000:]}',flush=True)
    if p.returncode or passed!=7:raise SystemExit(1)
