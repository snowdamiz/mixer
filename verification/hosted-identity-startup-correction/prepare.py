#!/usr/bin/env python3
"""Reconstruct the immutable startup candidate; never mutate live hosted source."""
import hashlib,json,shutil,subprocess,tarfile,tempfile
from pathlib import Path
O=Path(__file__).resolve().parent;R=O.parents[1];F=R/'verification/hosted-identity-startup-implementation'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def save(n,v):(O/n).write_text(json.dumps(v,indent=2)+'\n')
receipt=json.loads((F/'receipt.json').read_text()); manifest=json.loads((F/'tested-source-manifest.json').read_text())
assert sha(F/'tested-source.tar.gz')==receipt['sourceArchiveSHA256']
assert manifest['digest']==receipt['testedSourceDigest']=='c844efdf610f66280ef04cd5a47d033aad13105f60823e3eef60ba771fb026e2'
assert digest(manifest['files'])==manifest['digest']
S=Path(tempfile.mkdtemp(prefix='mixer-identity-startup-correction-')).resolve()
with tarfile.open(F/'tested-source.tar.gz') as t:
    assert all(m.isfile() and m.name in manifest['files'] for m in t.getmembers())
    t.extractall(S,filter='data')
assert {p:sha(S/p) for p in manifest['files']}==manifest['files']
for p,h in receipt['overlayFiles'].items():assert sha(S/p)==h
shutil.copytree(R/'hosted/deps',S/'hosted/deps',ignore=shutil.ignore_patterns('_build'))
deps={str(p.relative_to(S)):sha(p) for p in sorted((S/'hosted/deps').rglob('*')) if p.is_file() and '_build' not in p.relative_to(S).parts}
assert digest(deps)==receipt['dependencyDigest']
live={str(p.relative_to(R)):sha(p) for p in sorted((R/'hosted').rglob('*')) if p.is_file() and not {'deps','_build','__pycache__','cover'}.intersection(p.relative_to(R).parts) and p.name!='erl_crash.dump'}
shutil.copytree(F/'overlay',O/'overlay')
save('inputs.json',{'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'frozenPacket':'verification/hosted-identity-startup-implementation','frozenReceiptSHA256':sha(F/'receipt.json'),'frozenArchiveSHA256':sha(F/'tested-source.tar.gz'),'frozenSource':manifest['files'],'frozenSourceDigest':manifest['digest'],'frozenOverlay':receipt['overlayFiles'],'dependencies':deps,'dependencyDigest':digest(deps),'liveHosted':live,'liveHostedDigest':digest(live)})
save('state.json',{'scratch':str(S),'commands':[]})
print(S)
