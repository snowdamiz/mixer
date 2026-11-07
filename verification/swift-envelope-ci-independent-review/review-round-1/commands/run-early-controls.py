#!/usr/bin/env python3
"""Black-box controls with independent fixtures; never imports candidate code."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import time

ROUND=Path(__file__).resolve().parents[1]
REPO=ROUND.parents[2]
BASE=ROUND/'faults'
ROOT=BASE/'early-root'
PACK=ROOT/'verification/swift-envelope-ci-pack'
RUNNER=ROOT/'scripts/ci/check-analyzer-envelope.py'
(ROOT/'scripts/ci').mkdir(parents=True)
(ROOT/'verification').mkdir()
(ROOT/'runs').mkdir()
shutil.copyfile(REPO/'scripts/ci/check-analyzer-envelope.py',RUNNER)
shutil.copytree(REPO/'verification/swift-envelope-ci-pack',PACK)
original_runner=RUNNER.read_bytes()
(BASE/'early-toolchain/bin').mkdir(parents=True)
compiler=BASE/'early-toolchain/bin/rustc'
stub=(ROUND/'commands/early-compiler.py').read_text().replace("BASE = Path('REPLACED_BY_DRIVER')",'BASE = Path('+repr(str(BASE))+')')
compiler.write_text('#!'+sys.executable+'\n'+'\n'.join(stub.splitlines()[1:])+'\n');compiler.chmod(0o755)
original_compiler=compiler.read_bytes()
(BASE/'sentinel.txt').write_bytes(b'preserved-unowned-by-runner-sentinel')
results=[]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name, cfg=None, mutation=None, flags=None, optimize=False, output=None, launcher=None, expected='failed', admission=None, interrupt_retention=False):
    cfg={'case':name,**(cfg or {})}
    (BASE/'early-settings.json').write_text(json.dumps(cfg,sort_keys=True)+'\n')
    before={'runner':sha(RUNNER),'compiler':sha(compiler)}
    undo=mutation() if mutation else None
    out=output or ROOT/'runs'/name
    argv=[sys.executable,*(['-O'] if optimize else []),'-B',str(RUNNER),'--out',str(out),'--rustc',str(launcher or compiler),*(flags or [])]
    row={'name':name,'argv':argv,'cwd':str(REPO),'started_utc':datetime.now(timezone.utc).isoformat(),'fixture':cfg,'input_digests':before,'expected':expected,'admission_expected':admission}
    start=time.monotonic()
    env=dict(os.environ)
    env.update({'RUSTFLAGS':'--cfg INDEPENDENT_INJECTION','RUSTC_WRAPPER':'/owned-nonexistent-wrapper','RUST_TEST_THREADS':'77','RUST_TEST_RUN_IGNORED':'1','MIXER_ENVELOPE_SCRATCH':'/owned-unselected-scratch'})
    stdout=BASE/(name+'.stdout');stderr=BASE/(name+'.stderr')
    try:
        with stdout.open('xb') as so,stderr.open('xb') as se:
            proc=subprocess.Popen(argv,cwd=REPO,env=env,stdout=so,stderr=se,start_new_session=True)
            if interrupt_retention:
                deadline=time.monotonic()+30
                while proc.poll() is None and time.monotonic()<deadline:
                    if (out/'retained/sparse.failure.gz').exists():
                        proc.send_signal(signal.SIGTERM);row['sent_retention_SIGTERM_to_owned_pid']=proc.pid;break
                    time.sleep(.001)
            row['exit']=proc.wait(timeout=50)
        receipt_path=out/'receipt.json'
        receipt=json.loads(receipt_path.read_bytes()) if receipt_path.exists() else None
        row.update({'finished_utc':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,6),'receipt':str(receipt_path.relative_to(ROUND)) if receipt else None,'status':receipt.get('status') if receipt else 'no-output-receipt','errors':receipt.get('errors') if receipt else [],'commands':[r['name'] for r in receipt['commands']] if receipt else []})
        row['observed_failed']=row['exit']!=0 and (not receipt or receipt['status']=='failed')
        row['compile_attempted']='library-compile' in row['commands']
        row['control_passed']=row['observed_failed'] and (admission is None or row['compile_attempted']==admission)
        if receipt:
            row['postflight']={k:v['passed'] for k,v in receipt['postflight'].items()}
            row['cleanup']=receipt['cleanup']
            row['raw_streams_verified']=True
            for command in receipt['commands']:
                for stream in ('stdout','stderr'):
                    if stream in command:
                        p=out/command[stream]['path']
                        if p.stat().st_size!=command[stream]['bytes'] or sha(p)!=command[stream]['sha256']:row['raw_streams_verified']=False
            row['environment_scrubbed']=all(not any(k in r['environment'] for k in ('RUSTFLAGS','RUSTC_WRAPPER','RUST_TEST_THREADS','RUST_TEST_RUN_IGNORED','MIXER_ENVELOPE_SCRATCH')) for r in receipt['commands'])
            if cfg.get('mode')=='retention-interrupt': row['source_sparse_recoverable']=(out/'scratch/sparse.failure').exists()
            for p in (out/'scratch/owned-link',out/'scratch/owned-fifo'):
                if p.is_symlink() or p.exists():
                    s=p.lstat();row.setdefault('reviewer_fixture_cleanup',[]).append({'path':str(p.relative_to(ROUND)),'mode':s.st_mode,'symlink_target':os.readlink(p) if stat.S_ISLNK(s.st_mode) else None,'reason':'Record owned synthetic special object, then remove it for ordinary-file evidence transport; runner refusal remains preserved.'});p.unlink()
            row['sentinel_preserved']=(BASE/'sentinel.txt').read_bytes()==b'preserved-unowned-by-runner-sentinel'
        row['stdout']={'path':str(stdout.relative_to(ROUND)),'bytes':stdout.stat().st_size,'sha256':sha(stdout)}
        row['stderr']={'path':str(stderr.relative_to(ROUND)),'bytes':stderr.stat().st_size,'sha256':sha(stderr)}
    finally:
        if undo:undo()
        if RUNNER.read_bytes()!=original_runner:
            (BASE/(name+'.mutated-runner.py.txt')).write_bytes(RUNNER.read_bytes());RUNNER.write_bytes(original_runner)
        if compiler.read_bytes()!=original_compiler:
            (BASE/(name+'.mutated-compiler.py.txt')).write_bytes(compiler.read_bytes());compiler.write_bytes(original_compiler);compiler.chmod(0o755)
    results.append(row)
    (ROUND/'early-controls-progress.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'case':name,'control_passed':row['control_passed'],'status':row['status'],'compile_attempted':row['compile_attempted'],'elapsed_seconds':row['elapsed_seconds']},sort_keys=True),flush=True)


def change(relative, operation):
    p=PACK/relative;raw=p.read_bytes()
    def mutate():
        operation(p,raw)
        def undo():
            if p.is_symlink() or p.exists():p.unlink()
            p.write_bytes(raw)
        return undo
    return mutate


run('missing-member',mutation=change('api/no-clone.rs',lambda p,b:p.unlink()))
run('extra-hidden-member',mutation=lambda:((PACK/'.unexpected').write_bytes(b'extra'),lambda:(PACK/'.unexpected').unlink())[1])
run('mutated-library',mutation=change('source/library/analyzer.rs',lambda p,b:p.write_bytes(b+b'\n')))
run('mutated-overlay',mutation=change('source/producer/inputs/framing.rs',lambda p,b:p.write_bytes(b+b'\n')))
run('mutated-manifest',mutation=change('manifest.json',lambda p,b:p.write_bytes(b'{}')))
run('symlink-member',mutation=change('api/no-clone.rs',lambda p,b:(p.unlink(),p.symlink_to(PACK/'api/no-copy.rs'))))
run('fifo-member',mutation=change('api/no-clone.rs',lambda p,b:(p.unlink(),os.mkfifo(p))))
run('optimized-mutated-overlay',mutation=change('source/producer/inputs/framing.rs',lambda p,b:p.write_bytes(b+b'\n')),optimize=True)
(ROOT/'runs/existing').mkdir()
run('existing-output',output=ROOT/'runs/existing')
run('frozen-output',output=PACK/'unselected-output')
run('unknown-source-option',flags=['--source','/owned/arbitrary.rs'])
run('unknown-flags-option',flags=['--rustflags','-Awarnings'])
run('unknown-filter-option',flags=['--filter','independent'])
run('unsupported-release',cfg={'release':'1.98.2'},admission=False)
run('unsupported-host',cfg={'host':'x86_64-apple-darwin'},admission=False)
run('unsupported-nightly',cfg={'release':'1.99.0-nightly'},admission=False)
run('manager-identity',cfg={'identity':'manager'},admission=False)
run('mismatched-identity',cfg={'identity':'mismatch'},admission=False)
run('incomplete-identity',cfg={'identity':'incomplete'},admission=False)
run('duplicate-identity',cfg={'identity':'duplicate'},admission=False)
run('prospective-1-98-1',cfg={'release':'1.98.1'},admission=True)
run('prospective-1-99-0',admission=True)
run('partial-compile-failure')
run('missing-binary-spawn',cfg={'mode':'missing-binary'})
for mode in ('marker-change','inode-change','scratch-link','scratch-fifo','snapshot-change','runner-change','compiler-change'):
    run(mode,cfg={'mode':mode})
run('owned-descendant-timeout',cfg={'mode':'timeout-descendant'},admission=False)
run('retention-interrupted',cfg={'mode':'retention-interrupt'},interrupt_retention=True)
summary={'schema':1,'cases':len(results),'control_passed':sum(r['control_passed'] for r in results),'unexpected_acceptances':[r['name'] for r in results if not r['control_passed']],'scope':'Runner fault controls only; fake compiler success never qualifies product behavior.','results':results}
with (ROUND/'early-controls.json').open('x') as stream:json.dump(summary,stream,indent=2,sort_keys=True);stream.write('\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},sort_keys=True))
