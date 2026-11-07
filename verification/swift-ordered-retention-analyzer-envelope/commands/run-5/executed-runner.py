#!/usr/bin/env python3
"""Only bounded host fixture checks; never a VM, native or authority runner."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime,timezone

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
RUST=Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
UPSTREAM=[
('swift-ordered-retention-analyzer-design','c52828b9bbd2aea835871f1f6b68c6dd29281499ee080e5e52fefe525d1e92a8',67),
('swift-ordered-retention-analyzer-review','da87dd37e0983e212bbaf9658bc3177cb47c146bb13d82ddd2fea948c1966ebc',212),
('swift-ordered-retention-diagnostic-rust','c19bd3fb06e2db11a5e6ecb5aad8de2ca6ee19a35e50a5ba691ecb598bde40bf',186),
('swift-ordered-retention-diagnostic-completion','2e427447a34357ab4ff70eb220f56754f685a930edf4a89ebc29096fff3b73ba',222),
('swift-ordered-retention-diagnostic-completion-review','87a6fe21fd5c8f6590992aae8cc826e2502454686cf0d7a8c550acb7965827cc',158),
('swift-ordered-retention-analyzer-library','777e0a1b7a10d483bacb81475ad6c7af9a4d40fff64dd5ff2f3d893e1cd0fe63',270),
('swift-ordered-retention-analyzer-library-review','a5e21463c820277e1857a7eebcecdc7e45f40857b9c1dd39e8741f9b06a1bd4e',624),
('swift-ordered-retention-analyzer-fsm-contract','bde96e5f4f1b0ad5bc6366fee79a47f7a375247959191b206d8e7799ed4da193',245),
('swift-ordered-retention-analyzer-fsm-contract-review','101e6c9a67e41cce0e3c82c67ba92ef8025da19376b0578f8ddcdd694fb67212',528)]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def describe(p):return dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p))
def upstream():
    rows=[]
    for name,sealed,count in UPSTREAM:
        seal=ROOT/'verification'/name/'seal.json';assert digest(seal)==sealed,(name,'seal')
        members=json.loads(seal.read_text())['members'];assert len(members)==count
        for item in members:
            p=ROOT/item['path'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],item['path']
        rows.append(dict(packet=name,sha256=sealed,members=count,bytes=sum(x['bytes'] for x in members)))
    return rows
def main():
    name=sys.argv[1];assert name.startswith('run-') and '/' not in name
    run=BASE/'commands'/name;run.mkdir(exist_ok=False)
    scratch=BASE/'scratch'/name;scratch.mkdir(exist_ok=False)
    receipt=dict(schema=1,at=datetime.now(timezone.utc).isoformat(),scope='bounded standalone std-only fixture host; no semantic/real binding/target/native/capture',commands=[],source_inputs=[],scratch=str(scratch.relative_to(ROOT)))
    def write(): (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    def command(label,argv,env=None):
        p=subprocess.run([str(x) for x in argv],cwd=ROOT,capture_output=True,text=True,env=env)
        (run/(label+'.stdout')).write_text(p.stdout);(run/(label+'.stderr')).write_text(p.stderr)
        item=dict(name=label,argv=[str(x) for x in argv],status=p.returncode,stdout=label+'.stdout',stderr=label+'.stderr');receipt['commands'].append(item);write()
        if p.returncode:raise RuntimeError(label+' failed; retained outputs')
        return p.stdout
    try:
        receipt['upstream_before']=upstream();write()
        # These exact checks are custody/regression checks, never authority to
        # accept an OTA release or prove complete semantic source behavior.
        baseline=(ROOT/'verification/swift-ordered-retention-analyzer-library/src/analyzer.rs').read_bytes()
        assert (BASE/'src/analyzer.rs').read_bytes().startswith(baseline)
        assert digest(BASE/'tests/fixture_tests.rs')==digest(ROOT/'verification/swift-ordered-retention-analyzer-library/tests/fixture_tests.rs')
        for frozen in ['independent_tests.rs','private_io_tests.rs']:
            assert digest(BASE/'tests'/frozen)==digest(ROOT/'verification/swift-ordered-retention-analyzer-library-review'/frozen)
        command('logical-inventory',[sys.executable,'-B',BASE/'inventory.py'])
        command('step-inventory',[sys.executable,'-B',BASE/'step_inventory.py'])
        for name in ['inventory.py','step_inventory.py','logical-inventory.json','step-inventory.json']:
            shutil.copyfile(BASE/name,run/('executed-'+name))
        if (BASE/'inputs/preparation-freezes.json').exists():
            frozen=json.loads((BASE/'inputs/preparation-freezes.json').read_text())
            for item in frozen:
                p=ROOT/item['path'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],item['path']
            receipt['preparation_files_unchanged_before']=len(frozen)
        shutil.copyfile(__file__,run/'executed-runner.py')
        for name in ['src','tests','inputs']:
            shutil.copytree(BASE/name,run/'sources'/name)
        for file in sorted((run/'sources').rglob('*')):
            if file.is_file():receipt['source_inputs'].append(describe(file))
        receipt['source_tree_sha256']=hashlib.sha256(json.dumps(receipt['source_inputs'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
        receipt['tools']={label:dict(path=str(p),sha256=digest(p)) for label,p in [('python',Path(sys.executable)),('rustc',RUST)]}
        command('revision',['git','rev-parse','HEAD']);command('python-version',[sys.executable,'--version']);command('rust-version',[RUST,'--version','--verbose'])
        command('compile-library',[RUST,'--edition=2021','--crate-type=lib','-Dwarnings',run/'sources/src/analyzer.rs','-o',run/'library.rlib'])
        # The exact independent harness and private transport tests are copied,
        # appended only to this owned compile source, never to accepted sources.
        harness=run/'harness';(harness/'inputs').mkdir(parents=True)
        shutil.copytree(run/'sources/tests',harness/'tests')
        shutil.copytree(run/'sources/inputs',harness/'oracle-inputs')
        # include_bytes path is relative to tests; its fixture inputs are fixed.
        (harness/'inputs/oracle.bin').write_bytes((run/'sources/inputs/oracle.bin').read_bytes())
        framing=(run/'sources/src/analyzer.rs').read_bytes()+(run/'sources/tests/private_io_tests.rs').read_bytes()
        (harness/'inputs/framing.rs').write_bytes(framing)
        shutil.copyfile(run/'sources/src/envelope.rs',harness/'inputs/envelope.rs')
        shutil.copyfile(run/'sources/tests/independent_tests.rs',harness/'independent_tests.rs')
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',MIXER_REVIEW_SCRATCH=str(scratch/'review'),MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch/'foundation'),MIXER_ENVELOPE_SCRATCH=str(scratch/'envelope'),MIXER_ANALYZER_LIBRARY_HISTORICAL=str(BASE/'inputs/historical'))
        for part in ['review','foundation','envelope']:(scratch/part).mkdir()
        receipt['test_environment']={k:v for k,v in env.items() if k.startswith('MIXER_') or k=='PYTHONDONTWRITEBYTECODE'}
        command('compile-tests',[RUST,'--edition=2021','--test','-Dwarnings',harness/'independent_tests.rs','-o',run/'fixture-tests'])
        command('tests',[run/'fixture-tests','--test-threads=1','--nocapture'],env)
        receipt['status']='passed'
    except Exception as e:
        receipt['status']='failed';receipt['error']=str(e)
    finally:
        receipt['upstream_after']=upstream()
        if (BASE/'inputs/preparation-freezes.json').exists():
            for item in json.loads((BASE/'inputs/preparation-freezes.json').read_text()):
                p=ROOT/item['path'];assert p.stat().st_size==item['bytes'] and digest(p)==item['sha256'],item['path']
            receipt['preparation_files_unchanged_after']=len(frozen)
        receipt['retained_files']=[describe(p) for p in sorted(scratch.rglob('*')) if p.is_file()]
        with tarfile.open(run/'retained-owned-inputs.tar.gz','w:gz') as archive:archive.add(scratch,arcname='owned-scratch')
        shutil.rmtree(scratch);receipt['cleanup']='Owned scratch archived and removed after all synchronous children exited; no process/device discovery or native/capture work.'
        write();print(json.dumps(dict(status=receipt['status'],receipt=str(run/'receipt.json'),error=receipt.get('error')),indent=2))
    if receipt['status']!='passed':sys.exit(1)
if __name__=='__main__':main()
