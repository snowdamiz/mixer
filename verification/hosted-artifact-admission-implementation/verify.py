#!/usr/bin/env python3
"""Validate the producer packet; integrity is not independent semantic review."""
import argparse,hashlib,json,pathlib,subprocess,tarfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=pathlib.Path(__file__).resolve().parent
BASE='4586bb901b980e9beeca5f7bb826f8b62140a3b4'
DOC=ROOT/'docs/hosted-artifact-admission-implementation.md'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(p):return sha(p.read_bytes())
def patch():
    chunks=[]
    for p in sorted((OUT/'overlay').rglob('*')):
        if p.is_file():
            name=str(p.relative_to(OUT/'overlay'));s=p.read_text();assert s.endswith('\n')
            chunks.append(f'diff --git a/{name} b/{name}\nnew file mode 100644\n--- /dev/null\n+++ b/{name}\n@@ -0,0 +1,{len(s.splitlines())} @@\n'+''.join('+'+line+'\n' for line in s.splitlines()))
    return ''.join(chunks).encode()
def archive_check(path,want,inputs):
    assert digest(path)==want,path
    with tarfile.open(path,'r:gz') as tar:
        members=tar.getmembers();assert {m.name for m in members}==set(inputs)
        assert len(members)==len(inputs)
        for m in members:
            assert m.isfile() and sha(tar.extractfile(m).read())==inputs[m.name],m.name

def validate():
    run=OUT/'run-2';r=json.loads((run/'receipt.json').read_text());assert r['status']=='passed' and r['baseRevision']==BASE
    inputs=r['sourceInputs'];assert sha(json.dumps(inputs,sort_keys=True,separators=(',',':')).encode())==r['sourceTreeSHA256']
    archive_check(run/'source.tar.gz',r['sourceArchiveSHA256'],inputs)
    overlay={str(p.relative_to(OUT/'overlay')):digest(p) for p in (OUT/'overlay').rglob('*') if p.is_file()}
    assert len(overlay)==4 and set(overlay).issubset(inputs)
    assert all(name.startswith('hosted/lib/mixer_hosted/protocol/') or name=='hosted/test/mixer_hosted/protocol/artifact_admission_test.exs' for name in overlay)
    for name,want in inputs.items():
        if name in overlay:assert overlay[name]==want,name
        else:assert sha(subprocess.check_output(['git','show',f'{BASE}:{name}'],cwd=ROOT))==want,name
    for name,want in r['collectorInputs'].items():assert digest(ROOT/name)==want,name
    assert (OUT/'source.patch').read_bytes()==patch()
    assert len(r['dependencies'])==20 and all(len(d['archiveSHA256'])==64 for d in r['dependencies'])
    assert r['cleanup']=={'isolatedSourceRemoved':True,'ephemeralTestKeysPersisted':False,'existingProcessesOrDevicesTouched':False}
    assert r['caseCounts']=={'manifest':154,'origin':39,'namespace':14,'fixture':1,'assignmentOutOfScope':36}
    for c in r['commands']:
        assert c['exitCode']==0,c['label']
        assert digest(run/c['output'])==c['outputSHA256'],c['label']
    go=json.loads((run/'go-results.json').read_text());ex=json.loads((run/'elixir-results.json').read_text());assert go==ex
    assert len(go['results'])==208 and all(c['accepted']==c['expected'] for c in go['results'])
    assert go['fixtureFileSHA256']==inputs['services/protocol/testdata/signed-release-v3.json']
    assert go['corpusFileSHA256']==inputs['services/protocol/testdata/release-v3-cases.json']
    obs=json.loads((run/'parser-observations.json').read_text())['observations'];assert len(obs)==7
    assert obs[0]['result']['stats']['items']==4096 and obs[1]['result']['status']=='rejected'
    assert obs[5]['inputBytes']==6291456 and obs[5]['result']['status']=='admitted'
    assert obs[6]['inputBytes']==6291457 and obs[6]['result']['status']=='rejected'
    h=json.loads((run/'hosted/receipt.json').read_text());assert h['status']=='passed'
    archive_check(run/'hosted/source.tar.gz',h['source_archive_sha256'],h['inputs'])
    assert all(inputs[name]==want for name,want in h['inputs'].items())
    assert h['cleanup']=={'postgres_stopped':True,'scratch_removed':True}
    for c in h['commands']:
        assert c['exit_code']==c.get('expected_exit_code',0),c['label']
        assert digest(run/'hosted'/c['log'])==c['sha256']
    assert 'Result: 44 passed' in (run/'hosted/tests.log').read_text()
    assert json.loads((OUT/'manual-first-attempt-cleanup.json').read_text())['isolatedSourceRemoved']
    return r

def packet():
    files={str(DOC.relative_to(ROOT)):digest(DOC)}
    files.update({str(p.relative_to(ROOT)):digest(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='seal.json' and '__pycache__' not in p.parts})
    return files
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seal',action='store_true');args=parser.parse_args()
    r=validate();files=packet()
    if args.seal:
        assert not (OUT/'seal.json').exists(),'seal is immutable; use a new packet for changes'
        seal={'schema':1,'status':'producer-evidence-ready-independent-review-and-root-acceptance-pending','baseRevision':BASE,'sourceTreeSHA256':r['sourceTreeSHA256'],'files':files,'packetSHA256':sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())}
        (OUT/'seal.json').write_text(json.dumps(seal,indent=2)+'\n')
    else:
        seal=json.loads((OUT/'seal.json').read_text());assert seal['files']==files
        assert seal['packetSHA256']==sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())
    print(json.dumps({'status':'passed','sourceInputs':len(r['sourceInputs']),'overlayFiles':4,'sameInputComparisons':208,'hostedTests':44,'productionReleaseBuilt':True,'independentReview':'pending','rootAcceptance':'pending'}))
