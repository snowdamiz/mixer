from pathlib import Path
import hashlib,json,tarfile
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
s=json.loads((H/'seal.json').read_text())
assert hashlib.sha256(enc(s['files'])).hexdigest()==s['filesSHA256']
assert all(sha(H/n)==v for n,v in s['files'].items())
assert all(sha(R/n)==v for n,v in s['externalFiles'].items())
clean=json.loads((H/'implementation-source-manifest.json').read_text())
assert len(clean)==132 and all(sha(H/'implementation-source'/n)==v for n,v in clean.items())
count=0
with tarfile.open(H/'prototype-sources.tar.gz','r:gz') as tf:
    for member in tf.getmembers():
        kind,n=member.name.split('/',1)
        names=json.loads((H/(kind+'-final-diagnosis-source-manifest.json')).read_text())
        assert hashlib.sha256(tf.extractfile(member).read()).hexdigest()==names[n];count+=1
assert count==264
assert not (H/'owned-scratch').exists()
print(json.dumps({'sealedMembersVerified':len(s['files']),'cleanSourceMembersVerified':len(clean),'prototypeArchiveMembersVerified':count,'receiptSHA256':sha(H/'receipt.json'),'sealSHA256':sha(H/'seal.json'),'readOnly':True},indent=2))
