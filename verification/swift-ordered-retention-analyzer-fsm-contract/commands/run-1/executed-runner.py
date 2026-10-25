#!/usr/bin/env python3
"""Bounded host-only fixture checks and immutable source receipts."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
UPSTREAM=[
 ('verification/swift-ordered-retention-analyzer-design/seal.json','c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8',67),
 ('verification/swift-ordered-retention-analyzer-review/seal.json','da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc',212),
 ('verification/swift-ordered-retention-diagnostic-rust/seal.json','c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf',186),
 ('verification/swift-ordered-retention-diagnostic-completion/seal.json','2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba',222),
 ('verification/swift-ordered-retention-diagnostic-completion-review/seal.json','87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc',158)]
SOURCES=['AGENTS.md','mixer-product-plan.md','PLAN.md',
 'docs/swift-ordered-retention-analyzer.md','docs/swift-ordered-retention-analyzer-review.md',
 'verification/swift-ordered-retention-analyzer-root-review/acceptance.json',
 'verification/swift-ordered-retention-analyzer-design/interface_schema.py']
COPIED=['candidate__src__experimental__cache__borrowed.rs',
 'candidate__src__experimental_swift_reactor__cache.rs',
 'candidate__src__experimental_swift_reactor__control.rs',
 'verification__swift-ordered-retention-diagnostic-rust__writer.rs',
 'verification__swift-ordered-retention-diagnostic-rust__observer.rs',
 'verification__swift-ordered-retention-diagnostic-rust__source-code-table.json']
SOURCES += ['verification/swift-ordered-retention-analyzer-design/inputs/'+p for p in COPIED]

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(65536):h.update(b)
    return h.hexdigest()

def upstream():
    result=[]
    for path,expected,count in UPSTREAM:
        p=ROOT/path
        assert digest(p)==expected,(path,'seal drift')
        rows=json.loads(p.read_bytes())['members']
        assert len(rows)==count
        for row in rows:
            m=ROOT/row['path']
            assert m.stat().st_size==row['bytes'] and digest(m)==row['sha256'],row['path']
        result.append(dict(seal=path,sha256=expected,members=count))
    return result

def source_rows():
    return [dict(path=p,bytes=(ROOT/p).stat().st_size,sha256=digest(ROOT/p)) for p in SOURCES]

def main():
    assert sys.dont_write_bytecode
    run=BASE/'commands'/sys.argv[1]
    assert run.is_dir() and not (run/'result.json').exists()
    shutil.copyfile(__file__,run/'executed-runner.py')
    shutil.copyfile(BASE/'test_model.py',run/'executed-tests.py')
    before=upstream()
    sources=source_rows()
    for row in sources:
        target=BASE/'inputs'/row['path'].replace('/','__')
        if target.exists():assert digest(target)==row['sha256']
        else:shutil.copyfile(ROOT/row['path'],target)
    # Accepted copied wire authority must also equal its original source.
    wire=[]
    for suffix in ('writer.rs','observer.rs','source-code-table.json'):
        copied=ROOT/'verification/swift-ordered-retention-analyzer-design/inputs'/('verification__swift-ordered-retention-diagnostic-rust__'+suffix)
        original=ROOT/'verification/swift-ordered-retention-diagnostic-rust'/suffix
        assert digest(copied)==digest(original)
        wire.append(dict(copy=str(copied.relative_to(ROOT)),original=str(original.relative_to(ROOT)),sha256=digest(copied)))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    commands=[]
    for name,argv in [('python-version',[sys.executable,'--version']),
                      ('git-version',['git','--version']),
                      ('revision',['git','rev-parse','HEAD']),
                      ('finite-model',[sys.executable,'-B','-m','unittest','discover','-s',str(BASE),'-p','test_model.py','-v'])]:
        p=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,timeout=60)
        (run/(name+'.stdout')).write_bytes(p.stdout)
        (run/(name+'.stderr')).write_bytes(p.stderr)
        commands.append(dict(name=name,argv=argv,exit=p.returncode,stdout_sha256=digest(run/(name+'.stdout')),stderr_sha256=digest(run/(name+'.stderr'))))
    after=upstream()
    assert before==after
    assert sources==source_rows(),'consulted source drift'
    result=dict(schema=1,scope='Preparatory fixture FSM contract only',at=datetime.now(timezone.utc).isoformat(),
                python=dict(path=sys.executable,sha256=digest(Path(sys.executable))),
                source_snapshot=sources,source_tree_digest=hashlib.sha256(json.dumps(sources,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                upstream_before=before,upstream_after=after,wire_original_equality=wire,commands=commands,
                cleanup=dict(disposable_scratch_created=False,bytecode_created=False,synchronous_children_reaped=True,native_capture_or_target_started_or_queried=False),
                fullReplayAccepted=False,storedPrefixValidated=False,semanticMetricsValid=False,
                actual_rust_implementation_or_layout_qualification=False,
                passed=all(c['exit']==0 for c in commands))
    (run/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(dict(passed=result['passed'],commands=len(commands),upstream_members=sum(u['members'] for u in before),source_tree_digest=result['source_tree_digest']),sort_keys=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
