#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, os, re, subprocess, time
HERE = Path(__file__).resolve().parent
TREE = HERE / 'tree'
env = os.environ | {'PATH':'/opt/homebrew/opt/rustup/bin:' + os.environ['PATH'], 'CARGO_TARGET_DIR':str(HERE / 'build'), 'TMPDIR':str(HERE / 'tmp')}
def manifest(): return {str(p.relative_to(TREE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((TREE/'vm').rglob('*')) if p.is_file()}
before = json.loads((HERE / 'full-vm-input-manifest.json').read_text())
assert manifest() == before
commands=[]
for mode in ['debug','release']:
    for features, expected in [(['--all-features'],340), (['--features','experimental-swift-reactor'],226)]:
        argv=['cargo','test','--locked','--manifest-path','vm/Cargo.toml']+features
        if mode == 'release': argv += ['--release']
        argv += ['--','--test-threads=1']
        start=time.monotonic()
        p=subprocess.run(argv,cwd=TREE,env=env,capture_output=True,text=True)
        output=p.stdout+p.stderr
        count=sum(map(int,re.findall(r'test result: ok\. (\d+) passed;',output)))
        name=f'regression-{mode}-{"all" if expected==340 else "minimal-swift"}.log'
        (HERE/name).write_text(output)
        commands.append({'argv':argv,'cwd':str(TREE),'exit_code':p.returncode,'seconds':time.monotonic()-start,'passed':count,'expected':expected,'output':name,'output_sha256':hashlib.sha256(output.encode()).hexdigest()})
        (HERE/'independent-regressions.json').write_text(json.dumps({'commands':commands,'source_unchanged':manifest()==before},indent=2)+'\n')
        print(f'{mode} {features} exit={p.returncode} passed={count}',flush=True)
        if p.returncode or count!=expected: raise SystemExit(1)
assert manifest()==before
