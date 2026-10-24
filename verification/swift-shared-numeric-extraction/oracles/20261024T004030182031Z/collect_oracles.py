#!/usr/bin/env python3
"""Explicitly execute existing ignored integer/float development Node oracles."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, subprocess, tarfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MAIN=HERE/'results/20261024T003757200365Z'
STAMP=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
RUN=HERE/'build'/('oracles-'+STAMP)
OUT=HERE/'oracles'/STAMP
RUN.mkdir(parents=True,exist_ok=False);OUT.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
jsonbytes=lambda x:(json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
commands=[];variants=[];scope=[]
env=dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'])
shutil.copy2(HERE/'collect_oracles.py',OUT/'collect_oracles.py')
def manifest(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}
def command(name,argv,cwd,target=None,closure=None):
    if closure is not None:assert manifest(cwd)==closure
    penv=dict(env)
    if target:penv['CARGO_TARGET_DIR']=str(target)
    p=subprocess.run(argv,cwd=cwd,env=penv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1200)
    log=OUT/(name+'.log');log.write_bytes(p.stdout)
    if closure is not None:assert manifest(cwd)==closure
    commands.append(dict(name=name,argv=argv,cwd=str(cwd),target=str(target) if target else None,exit=p.returncode,log=log.name,logSHA256=sha(log),sourceBeforeAfterVerified=closure is not None))
    print(name,p.returncode,flush=True)
    if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')[-6000:])
    return p.stdout.decode(errors='replace')
try:
    command('rustc-version',['rustc','-vV'],ROOT)
    command('cargo-version',['cargo','-V'],ROOT)
    command('node-version',['node','--version'],ROOT)
    for variant,filename in [('baseline','baseline-source.tar.gz'),('candidate','product-source.tar.gz')]:
        archive=MAIN/filename
        with tarfile.open(archive) as tf:tf.extractall(RUN/variant,filter='data')
        dest=RUN/variant/'vm';closure=manifest(dest)
        (OUT/(variant+'-manifest.json')).write_bytes(jsonbytes(closure))
        variants.append(dict(name=variant,archive=str(archive.relative_to(ROOT)),archiveSHA256=sha(archive),treeSHA256=hashlib.sha256(jsonbytes(closure)).hexdigest()))
        for feature,flags in [('default',[]),('span',['--features','experimental-span-execution']),('all',['--all-features'])]:
            for profile in ['debug','release']:
                name=variant+'-'+feature+'-'+profile
                target=RUN/(name+'-target')
                argv=['cargo','test','--locked','--offline',*flags]
                if profile=='release':argv+=['--release']
                argv+=['--test','differential','--test','float_differential']
                listed=command(name+'-list',argv+['--','--ignored','--list'],dest,target,closure)
                tests=[line for line in listed.splitlines() if line.endswith(': test')]
                assert len(tests)==6
                executed=command(name,argv+['--','--ignored','--nocapture','--test-threads=1'],dest,target,closure)
                assert executed.count('test result: ok. 3 passed; 0 failed; 0 ignored;')==2
                summary=[line for line in executed.splitlines() if 'differential cases matched:' in line or 'integer-v1 oracle cases:' in line]
                scope.append(dict(variant=variant,feature=feature,profile=profile,tests=tests,count=len(tests),summaries=summary))
    status='passed-explicit-existing-development-oracles-only'
except Exception:
    status='failed'
    raise
finally:
    (OUT/'receipt.json').write_bytes(jsonbytes(dict(schema=1,status=status,mainReceipt=str((MAIN/'receipt.json').relative_to(ROOT)),revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),scope='Existing integer and float differential Node oracles explicitly run; no Swift target or device.',commands=commands,variants=variants,executed=scope)))
    print(str(OUT),flush=True)
