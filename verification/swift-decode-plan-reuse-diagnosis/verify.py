#!/usr/bin/env python3
"""Read-only finite packet verification; no build, guest or native execution."""
from pathlib import Path
import gzip,hashlib,json,re,stat,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((H/n).read_text())
seal=read('seal.json')
actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file()}
assert actual==set(seal['files'])|{'seal.json'}
for n,v in seal['files'].items():
 p=H/n;assert sha(p)==v,(n,'content mismatch');assert p.stat().st_mode&0o222==0,(n,'writable')
assert (H/'seal.json').stat().st_mode&0o222==0
for n,v in seal['externalFiles'].items():assert sha(R/n)==v,(n,'external binding drift')
assert not (H/'owned-scratch').exists()
r=read('receipt.json');a=read('command-audit.json');s=read('source-selection.json')
assert not r['liveAcceptance'] and not r['fullSuiteRun'] and not r['exactPhaseHelperRun']
assert r['actualInheritedTests']==12 and r['diagnosticTestsDebug']==r['diagnosticTestsRelease']==9
assert sum(a[f'sealed-inherited-{n:02}']['passedTests'] for n in range(1,15))==12
assert [n for n,x in a.items() if x['zeroTestNonqualifying']]==r['zeroTestNonqualifyingCommands']
assert all(not a[n]['qualifyingCommand'] for n in r['zeroTestNonqualifyingCommands'])
for label in ('qualified-finite-debug','qualified-finite-release','qualified-frozen','profile-admission'):
 p=read('commands/'+label+'/receipt.json');assert p['passed'] and p['sourceUnchanged'];assert p['sourceManifestSHA256']==s['prototype132FileClosure']
 for f in ('stdout','stderr'):assert sha(H/'commands'/label/f)==p[f+'SHA256']
for label in ('qualified-baseline-observation','qualified-baseline-frozen','baseline-profile-admission'):
 p=read('commands/'+label+'/receipt.json');assert p['passed'] and p['sourceUnchanged'];assert p['sourceManifestSHA256']==s['baselineControl132FileClosure']
assert all(x['streamsClosed'] and x['ownedGroupAbsent'] for x in a.values())
base=read('baseline-manifest.json');source=read('source-manifest.json')
assert len(base)==len(source)==132
assert [n for n in base if base[n]!=source[n]]==s['changedFiles']
for n,v in base.items():assert sha(R/'vm'/n)==v,(n,'live source drift')
for n,v in source.items():assert sha(H/'source'/n)==v
bn=(H/'commands/qualified-baseline-frozen/stdout').read_text();dn=(H/'commands/qualified-frozen/stdout').read_text()
normalize=lambda t:'\n'.join(x for x in t.splitlines() if not x.startswith('test result:'))
assert normalize(bn)==normalize(dn)
b=(H/'commands/qualified-baseline-observation/stdout').read_text();d=(H/'commands/qualified-finite-debug/stdout').read_text();o=(H/'commands/qualified-finite-release/stdout').read_text()
for pattern in (r'PLAN_IR .*$',r'PLAN_LRU .*$'):assert re.findall(pattern,b,re.M)==re.findall(pattern,d,re.M)==re.findall(pattern,o,re.M)
assert read('comparison.json')['cases']['false']['repeatSavingsCredits']==-462
assert read('comparison.json')['cases']['true']['repeatSavingsCredits']==95794
assert read('profile-admission.json')['combinedHeadroomBytes']==1647458
cleanup=read('cleanup.json');assert cleanup['scratchAbsent'] and cleanup['ownedGroupsAbsent']
for arc in cleanup['binaryArchives']:
 p=H/arc['archive'];assert sha(p)==arc['archiveSHA256'];data=gzip.decompress(p.read_bytes());assert len(data)==arc['original']['bytes'];assert hashlib.sha256(data).hexdigest()==arc['original']['sha256']
ps=subprocess.check_output(['/bin/ps','-axo','pid=,pgid=,comm='],text=True)
groups=set(cleanup['processGroupsChecked']);assert not [x for x in ps.splitlines() if len(x.split())>=2 and int(x.split()[1]) in groups]
print(json.dumps({'verifiedFiles':len(seal['files']),'sealSHA256':sha(H/'seal.json'),'prototypeClosure':s['prototype132FileClosure'],'diagnosticDebug':9,'diagnosticRelease':9,'actualInheritedTests':12,'FrozenTestsEachSide':3,'nonqualifyingZeroTestCommands':4,'liveUnchanged':True,'scope':'finite isolated diagnosis only; full-suite/exact-phase/root/independent review pending'},sort_keys=True))
