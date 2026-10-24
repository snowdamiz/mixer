#!/usr/bin/env python3
"""Fresh separate metadata replay and recorded final saved-evidence checks."""
from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, sys, tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=Path(sys.argv[1]).resolve()
receipt=json.loads((OUT/'receipt.json').read_text())
assert receipt['status']=='passed-selected-native-outcomes-accounting-review-separate'
encode=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(encode(x)).hexdigest()
def manifest(p):return {str(x.relative_to(p)):sha(x) for x in sorted(p.rglob('*')) if x.is_file()}
commands=[]
result=dict(schema=1,status='failed',scope='one metadata-only Debug/all-features unit layout test, separate from 92 native behavior test executions; source association and saved-evidence validation',
            sourceTreeSHA256=receipt['sourceTreeSHA256'],commands=commands)
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
def run(name,argv,cwd,closure=None,target=None):
    if closure is not None:assert manifest(cwd)==closure
    actual=dict(env)
    if target is not None:actual['CARGO_TARGET_DIR']=str(target)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    p=subprocess.run(argv,cwd=cwd,env=actual,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=600)
    log=OUT/(name+'.log');log.write_bytes(p.stdout)
    if closure is not None:assert manifest(cwd)==closure
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,
                         exit=p.returncode,log=log.name,logSHA256=sha(log),startedUTC=started,
                         completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                         sourceClosureSHA256=digest(closure) if closure else None))
    print(name,p.returncode,flush=True)
    assert p.returncode==0,p.stdout.decode(errors='replace')[-10000:]
    return p.stdout.decode(errors='replace')
try:
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    build=HERE/'build'/('final-metadata-'+stamp)
    build.mkdir(parents=True)
    with tarfile.open(OUT/'candidate-source.tar.gz') as tf:tf.extractall(build/'source',filter='data')
    dest=build/'source/vm'
    execution=dest/'src/experimental_swift_reactor/execution.rs'
    execution.write_text(execution.read_text()+'\n'+(OUT/'inputs/producer-owner-layout-probe.rs').read_text())
    operation=dest/'src/experimental_swift_reactor/value_operations.rs'
    operation.write_text(operation.read_text()+'\n'+(OUT/'inputs/producer-operation-layout-probe.rs').read_text())
    calls='execution::operations_owner_layout_probe(); execution::value_operations::operations_layout_probe();'
    module=dest/'src/experimental_swift_reactor/mod.rs'
    module.write_text(module.read_text()+'\npub(crate) fn value_layout_probe(){'+calls+'}\n')
    lib=dest/'src/lib.rs'
    lib.write_text(lib.read_text()+'\n#[cfg(feature="experimental-swift-reactor")] pub fn value_layout_probe(){experimental_swift_reactor::value_layout_probe();}\n')
    (dest/'examples').mkdir(exist_ok=True)
    (dest/'examples/value-layout.rs').write_text('fn main(){mixer_vm::value_layout_probe();}\n')
    execution.write_text(execution.read_text()+'\n#[cfg(test)] #[test] fn value_layout_only(){super::value_layout_probe();}\n')
    closure=manifest(dest)
    assert closure==json.loads((OUT/'inputs/producer-candidate-layout-closure.json').read_text())
    (OUT/'metadata-source-manifest.json').write_bytes(encode(closure))
    target=build/'metadata-target'
    output=run('independent-metadata-build',['cargo','test','--locked','--offline','--lib','--all-features','--no-run','--message-format=json'],dest,closure,target)
    binaries=[]
    for line in output.splitlines():
        try:row=json.loads(line)
        except ValueError:continue
        if row.get('reason')=='compiler-artifact' and row.get('profile',{}).get('test') and row.get('executable'):binaries.append(Path(row['executable']))
    assert len(binaries)==1
    binary=binaries[0]
    listing=run('independent-metadata-list',[str(binary),'--list'],dest,closure,target)
    runtime=run('independent-metadata-run',[str(binary),'value_layout_only','--nocapture','--test-threads=1'],dest,closure,target)
    assert re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;',runtime)==[('1','0')]
    markers=['value_owner|','value_owner_field|','value_bounds|','value_inventory|','value_position|']
    records=[]
    for line in runtime.splitlines():
        indices=[line.index(marker) for marker in markers if marker in line]
        if indices:records.append(line[min(indices):])
    producer=json.loads((OUT/'inputs/producer-receipt.json').read_text())
    expected=next(x for x in producer['layouts'] if x['label']=='candidate' and x['configuration']=='all' and x['profile']=='debug' and x['cfg']=='unit')
    assert records==expected['records']
    result['metadata']=dict(binary=str(binary),sha256=sha(binary),listedTests=[x[:-6] for x in listing.splitlines() if x.endswith(': test')],
                            selectedTests=[x[:-6] for x in listing.splitlines() if x.endswith(': test') and 'value_layout_only' in x],
                            passed=1,ignored=0,records=records,sourceClosureSHA256=digest(closure))
    run('final-accounting-audit',['python3','-B',str(HERE/'audit_accounting.py'),str(OUT)],ROOT)
    run('final-saved-verification',['python3','-B',str(HERE/'verify.py'),str(OUT)],ROOT)
    result['status']='passed-separate-metadata-replay-and-final-saved-checks'
finally:
    (OUT/'completion-receipt.json').write_bytes(encode(result))
