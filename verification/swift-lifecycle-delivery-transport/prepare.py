"""Lossless Git transport for four sealed large accounting JSON files."""
from pathlib import Path
import gzip, hashlib, json, re, sys, zlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
P=ROOT/'verification/swift-reactor-lifecycle-accounting'
PREVIOUS=ROOT/'verification/swift-calls-dispatch-delivery-transport'
SEAL='02b53f531a4cb4852cc7e99104d13bb09e969f9d6b018c4d5d8fd6cd0d3dbbdd'
NAMES=['paired-layouts.json','inventory-final.json','inventory.json','discovery-final-preinstall/inventory.json']
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(1048576):h.update(b)
    return h.hexdigest()
def bound(p):return {'bytes':p.stat().st_size,'sha256':digest(p)}
assert digest(P/'seal.json')==SEAL
authority=json.loads((P/'seal.json').read_text())
entries=[]
(HERE/'payloads').mkdir(exist_ok=True)
for name in NAMES:
    source=P/name
    assert not source.is_symlink() and digest(source)==authority['files'][name]
    payload='payloads/'+name.replace('/','--')+'.gz';destination=HERE/payload
    with source.open('rb') as f,destination.open('xb') as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0,compresslevel=9) as compressed:
            while b:=f.read(1048576):compressed.write(b)
    h=hashlib.sha256();n=0
    with gzip.open(destination,'rb') as f:
        while b:=f.read(1048576):h.update(b);n+=len(b)
    assert n==source.stat().st_size and h.hexdigest()==authority['files'][name]
    entries.append({'path':str(source.relative_to(ROOT)),'bytes':n,'sha256':h.hexdigest(),'mode':'100644','payload':payload,'gzip':bound(destination)})
manifest={'schema':1,'scope':'Exact-byte transport only; original sealed evidence remains unchanged',
    'authority':{str((P/'seal.json').relative_to(ROOT)):bound(P/'seal.json')},
    'entries':entries,'excludedRawPaths':[x['path'] for x in entries],'normalization':'none'}
mp=HERE/'transport-manifest.json';mp.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
expected={r['path']:(r['bytes'],r['sha256'],r['payload']) for r in entries}
restore=(PREVIOUS/'restore.py').read_text()
restore=restore.replace('two selected missing raw evidence files','four selected missing raw evidence files')
restore=re.sub(r"MANIFEST_SHA256 = '[0-9a-f]+'",'MANIFEST_SHA256 = '+repr(digest(mp)),restore,count=1)
start=restore.index('EXPECTED = {');end=restore.index('\nCHUNK =',start)
restore=restore[:start]+'EXPECTED = '+repr(expected)+restore[end:]
restore=restore.replace("len(data['entries']) == 2, 'fixed two-entry manifest required'","len(data['entries']) == 4, 'fixed four-entry manifest required'")
start=restore.index('def authority_check(');end=restore.index('\ndef main(',start)
replacement='''def authority_check(root_fd, data):
    name = 'verification/swift-reactor-lifecycle-accounting/seal.json'
    require(set(data['authority']) == {name}, 'authority set drift')
    row = data['authority'][name]
    require(row['sha256'] == %r, 'wrong accounting seal')
    fd = open_regular(root_fd, name)
    with os.fdopen(fd, 'rb') as f:
        raw = f.read(row['bytes'] + 1)
    require(len(raw) == row['bytes'] and digest_bytes(raw) == row['sha256'], 'authority drift')
    sealed = json.loads(raw)['files']
    prefix = 'verification/swift-reactor-lifecycle-accounting/'
    for entry in data['entries']:
        require(entry['path'].startswith(prefix), 'unselected authority path')
        require(sealed[entry['path'][len(prefix):]] == entry['sha256'], 'raw target not selected by original seal')
''' % SEAL
restore=restore[:start]+replacement+restore[end:]
(HERE/'restore.py').write_text(restore)
(HERE/'controls.py').write_bytes((PREVIOUS/'controls.py').read_bytes())
receipt={'argv':[sys.executable,'-B',str(Path(__file__))],'script':bound(Path(__file__)),'pythonVersion':sys.version,'pythonExecutable':str(Path(sys.executable).resolve()),'python':bound(Path(sys.executable).resolve()),'zlibVersion':zlib.ZLIB_VERSION,
    'manifest':bound(mp),'originalSealSHA256':SEAL,'originalRawBytes':sum(x['bytes'] for x in entries),'compressedBytes':sum(x['gzip']['bytes'] for x in entries),
    'existingEvidenceUnchanged':all(digest(ROOT/x['path'])==x['sha256'] for x in entries),'reusedControls':bound(PREVIOUS/'controls.py'),'restoreBasis':bound(PREVIOUS/'restore.py'),'compilerOrRuntimeExecuted':False}
(HERE/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'rawBytes':receipt['originalRawBytes'],'compressedBytes':receipt['compressedBytes'],'manifestSHA256':digest(mp)}))
