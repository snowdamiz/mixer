#!/usr/bin/env python3
"""Bounded exact host reproduction of root's combined five-test CI noise step."""
from datetime import datetime, timezone
import hashlib, json, os, subprocess, tempfile
from pathlib import Path
here=Path(__file__).resolve().parent
review=here.parent
root=review.parents[1]
base=json.loads((review/'receipt.json').read_text())
source=Path(base['private_source']['repaired'])
env=dict(os.environ)
env['PATH']='/opt/homebrew/opt/rustup/bin:'+env['PATH']
env['MIXER_ALLOCATOR_NOISE']='1'
env.pop('MIXER_GUEST_ARC_OOM_SIZE',None)
env['CARGO_TARGET_DIR']=tempfile.mkdtemp(prefix='mixer-combined-observer-ci-noise-')
def sha(data):return hashlib.sha256(data).hexdigest()
def manifest():return {str(p.relative_to(source)):sha(p.read_bytes()) for p in sorted(source.rglob('*')) if p.is_file()}
def tree(files):return sha(json.dumps(files,sort_keys=True).encode())
before=manifest()
assert tree(before)==base['repaired_tree_sha256']
base_command=['cargo','test','--locked','--manifest-path','vm/Cargo.toml','--features','experimental-span-execution,experimental-capability-native','--test','span_function_cache_allocations','--test','span_execution_allocations','--test','experimental_allocations','--test','experimental_capability_guest_allocations','--test','capability_ffi_allocations']
checks=[]
for release in [False,True]:
    name='release' if release else 'debug'
    command=base_command+(['--release'] if release else [])+['--','--nocapture']
    logfile=here/'logs'/(name+'.log')
    with logfile.open('w') as log:
        log.write('CWD: '+str(source)+'\nCOMMAND: '+repr(command)+'\nENV: '+repr({'PATH':env['PATH'],'MIXER_ALLOCATOR_NOISE':'1','CARGO_TARGET_DIR':env['CARGO_TARGET_DIR']})+'\nTIMEOUT_SECONDS: 240\n');log.flush()
        result=subprocess.run(command,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
        log.write('\nEXIT: '+str(result.returncode)+'\n')
    output=logfile.read_text()
    assert result.returncode==0
    assert output.count('test result: ok. 1 passed; 0 failed; 0 ignored')==5
    assert 'eight argument/completion payloads: (16, 8388608, 8388608)' in output
    assert manifest()==before
    checks.append({'name':name,'command':command,'environment':{'PATH':env['PATH'],'MIXER_ALLOCATOR_NOISE':'1','CARGO_TARGET_DIR':env['CARGO_TARGET_DIR']},'timeout_seconds':240,'exit':result.returncode,'passed_test_processes':5,'source_before_sha256':tree(before),'source_after_sha256':tree(manifest()),'log':str(logfile.relative_to(root)),'log_sha256':sha(logfile.read_bytes())})
    print(name+': 5 test processes passed',flush=True)
receipt={'observed_utc':datetime.now(timezone.utc).isoformat(),'status':'passed','command':'PATH=/opt/homebrew/opt/rustup/bin:$PATH python3 verification/remaining-allocator-observers-review/combined-ci-noise/run.py','baseline_revision':base['baseline_revision'],'source_tree_sha256':tree(before),'base_review_seal_sha256':sha((review/'seal.json').read_bytes()),'retained_snapshot_sha256':sha((review/'tested-vm-snapshot.tar').read_bytes()),'runner_sha256':sha(Path(__file__).read_bytes()),'tools':{k:subprocess.check_output(v,env=env,text=True).strip() for k,v in [('rustc',['rustc','-Vv']),('cargo',['cargo','-V'])]},'checks':checks,'scope':'Local Mac host execution of exact proposed CI test commands; hosted CI remains separate. No physical device, immutable published consumer, release or GA qualification.'}
(here/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
