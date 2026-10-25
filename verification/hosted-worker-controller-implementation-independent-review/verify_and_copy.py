#!/usr/bin/env python3
"""Independent read-only producer binding check and isolated replay preparation."""
import hashlib, json, os, platform, shutil, subprocess, tarfile, tempfile
from pathlib import Path

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
HERE = Path(__file__).resolve().parent
PRODUCER = ROOT / 'verification/hosted-worker-controller-implementation'
EXPECTED_RECEIPT = 'fb71bcb1cc076b121a26e075c8e1bf8c2703bc5a659686e4a6ae861b855dc68a'
EXPECTED_TREE = '6f47612d9bf3118fb50be51f36dc05bbd724bd60416a5cdec0b1fa6299042e95'
EXPECTED_ARCHIVE = 'd6894fdae991b51485e7bec04a86027f87d84261ddc527e292e072c8b8dd55b7'

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def check(entry):
    p=ROOT/entry['path']
    assert p.stat().st_size==entry['bytes'], str(p)
    assert sha(p)==entry['sha256'], str(p)
    return p

def main():
    assert sha(PRODUCER/'receipt.json')==EXPECTED_RECEIPT
    receipt=json.loads((PRODUCER/'receipt.json').read_text())
    source=json.loads((PRODUCER/'source-manifest.json').read_text())
    assert hashlib.sha256(json.dumps(source['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()==EXPECTED_TREE==receipt['source_tree_sha256']
    assert sha(PRODUCER/'source-snapshot.tar.gz')==EXPECTED_ARCHIVE
    for name in ['source_manifest','dependency_manifest','jason_beams','source_archive']: check(receipt[name])
    counts={}
    for name in ['source-manifest.json','dependency-files.json','jason-beams.json']:
        entries=json.loads((PRODUCER/name).read_text())['files']
        for e in entries: check(e)
        counts[name]=len(entries)
    for e in receipt['artifacts']: check(e)
    for e in receipt['runtime_binary_inputs']: check(e)
    lock=json.loads((ROOT/'hosted-worker-controller/package-lock.json').read_text())
    inventory=json.loads((ROOT/'hosted-worker-controller/THIRD_PARTY.yml').read_text())
    deps={e['lockPath']:e for e in inventory['packages']}
    assert len(deps)==len(lock['packages'])-1==58
    for path,p in lock['packages'].items():
        if not path: continue
        d=deps[path]
        for k in ['version','license','integrity','resolved']: assert d[k]==p[k],(path,k)
        assert d['purpose'] and d['scope']=='development-only' and not d['installScriptsExecuted']
    expected={e['path']:e for e in source['files']}
    with tarfile.open(PRODUCER/'source-snapshot.tar.gz') as archive:
        assert set(archive.getnames())==set(expected)
        for member in archive:
            assert member.isfile() and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
            assert hashlib.sha256(archive.extractfile(member).read()).hexdigest()==expected[member.name]['sha256']
        scratch=Path(tempfile.mkdtemp(prefix='mixer-controller-independent-'))
        archive.extractall(scratch,filter='data')
    shutil.copytree(ROOT/'hosted-worker-controller/node_modules',scratch/'hosted-worker-controller/node_modules',symlinks=True)
    node=Path('/Users/andreyyurlov/.local/share/fnm/node-versions/v22.23.3/installation/bin/node')
    npm=node.parent/'npm'
    tools=[]
    for argv in [[str(node),'--version'],[str(node),str(npm),'--version'],[str(node),'node_modules/typescript/bin/tsc','--version'],[str(node),'-e','for(const p of ["miniflare","workerd","@cloudflare/workers-types","typescript"])console.log(p+"="+require(p+"/package.json").version)']]:
        r=subprocess.run(argv,cwd=scratch/'hosted-worker-controller',capture_output=True,text=True)
        tools.append({'argv':argv,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
        assert r.returncode==0,tools[-1]
    report={'status':'passed','receipt_sha256':EXPECTED_RECEIPT,'source_tree_sha256':EXPECTED_TREE,'archive_sha256':EXPECTED_ARCHIVE,'verified_counts':counts,'producer_artifacts':len(receipt['artifacts']),'runtime_binary_inputs':len(receipt['runtime_binary_inputs']),'dependency_entries':58,'scripts_executed':0,'tools':tools,'scratch':str(scratch),'platform':platform.platform(),'no_git_inspected':True}
    (HERE/'bindings.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__': main()
