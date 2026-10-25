"""Offline exact package verification; no producer, listener or native command."""
import hashlib,json,pathlib,stat,tarfile
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def check(p,r):
 assert p.is_file() and not p.is_symlink() and p.resolve()==p,str(p)
 raw=p.read_bytes();assert len(raw)==r['bytes'] and sha(raw)==r['sha256'] and stat.S_IMODE(p.stat().st_mode)==r['mode'],str(p)
def main():
 handoff=read(B/'handoff.json')
 for name,r in handoff['members'].items():check(ROOT/name,r)
 binding=read(B/'source-bindings.json');frozen={}
 for source in binding['archives']:
  copied=B/'inputs'/(source['prefix']+'-sources.tar.gz')
  assert sha(copied.read_bytes())==source['sha256'] and sha((ROOT/source['path']).read_bytes())==source['sha256']
  with tarfile.open(copied) as tar:
   files=[m for m in tar.getmembers() if m.isfile()];assert len(files)==source['files']
   for member in files:
    raw=tar.extractfile(member).read();frozen[member.name]={'sha256':sha(raw),'bytes':len(raw)}
 assert frozen==binding['frozenFiles']
 for name,r in binding['derivativeFiles'].items():
  p=B/'sources'/name;assert p.stat().st_size==r['bytes'] and sha(p.read_bytes())==r['sha256']
 changed=[name for name in frozen if frozen[name]!=binding['derivativeFiles'][name]]
 assert sorted(changed)==sorted(binding['changedEndpoints']) and len(changed)==2
 for archive_name,manifest_name,prefix in [('review-source-package.tar.gz','source-package-manifest.json','package/'),('synthetic-evidence.tar.gz','synthetic-evidence-manifest.json','')]:
  manifest=read(B/manifest_name)
  with tarfile.open(B/archive_name) as tar:
   files=tar.getmembers();assert len(files)==len(manifest) and len(set(m.name for m in files))==len(files)
   for member in files:
    assert member.name.startswith(prefix) and '..' not in pathlib.PurePosixPath(member.name).parts
    name=member.name[len(prefix):];r=manifest[name];assert member.mode==r['mode']
    if r['kind']=='symlink':assert member.issym() and member.linkname==r['target']
    elif r['kind']=='directory':assert member.isdir()
    else:
     assert member.isfile();raw=tar.extractfile(member).read();assert len(raw)==r['bytes'] and sha(raw)==r['sha256']
 receipt=read(B/'receipt.json');assert receipt['hostMethods']==45 and receipt['foundationRows']==80 and receipt['ownedWorkingStoresAbsent'] and receipt['gaAccepted'] is False and receipt['nativeSettingsPassed'] is False
 assert all(not (B/folder).exists() for folder in ['synthetic-attempts','witnesses','owned-host-scratch'])
 assert read(B/'controls.json')['passed'] and read(B/'host-controls.json')['passed']
 print(json.dumps(dict(passed=True,handoffSHA256=sha((B/'handoff.json').read_bytes()),sealedMembers=len(handoff['members']),sourceMembers=72,changedEndpoints=2,unchangedSources=70,sourceReviewArchiveSHA256=sha((B/'review-source-package.tar.gz').read_bytes()),syntheticFiles=len(read(B/'synthetic-evidence-manifest.json')),scope='offline exact verification only; no native acceptance'),sort_keys=True))
if __name__=='__main__':main()
