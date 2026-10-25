#!/usr/bin/env python3
"""Archive exact finite source and bind unchanged paths before retirement."""
import difflib,hashlib,json,pathlib,tarfile
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def encoded(value):return (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
def manifest(root):return {str(p.relative_to(root)):sha(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
original=json.loads((OUT/'baseline-manifest.json').read_text())
assert {name:sha((ROOT/'vm'/name).read_bytes()) for name in original}==original
sources={}
for label,root,names in [('live-baseline',ROOT/'vm',original),('baseline',OUT/'.scratch/baseline',manifest(OUT/'.scratch/baseline')),('candidate',OUT/'.scratch/candidate',manifest(OUT/'.scratch/candidate'))]:
 data=encoded(names);(OUT/f'{label}-source-manifest.json').write_bytes(data)
 archive=OUT/f'{label}-source.tar.gz'
 with tarfile.open(archive,'w:gz') as tar:
  for name in names:tar.add(root/name,arcname=name,recursive=False)
 sources[label]={'manifestSHA256':sha(data),'archiveSHA256':sha(archive.read_bytes()),'fileCount':len(names),'sourceBytes':sum((root/name).stat().st_size for name in names)}
candidate=OUT/'.scratch/candidate'; baseline=OUT/'.scratch/baseline'
patch=[]
for name in original:
 a=(ROOT/'vm'/name).read_text();b=(candidate/name).read_text()
 if a!=b:patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='live/'+name,tofile='candidate/'+name))
(OUT/'candidate.patch').write_text(''.join(patch))
def span(text,start,end):return text.split(start,1)[1].split(end,1)[0]
generic='src/experimental/cache/borrowed.rs'; swift='src/experimental_swift_reactor/cache.rs'
a=(baseline/generic).read_text();b=(candidate/generic).read_text();sa=(baseline/swift).read_text();sb=(candidate/swift).read_text()
checks={
 'generic-pin-body':(span(a,'pub(crate) fn pin<M: CacheMode>','pub(crate) struct CacheFields'),span(b,'pub(crate) fn pin<M: CacheMode>','pub(crate) struct CacheFields')),
 'generic-hit-branch':(span(a,'let index = if let Some(index) = hit {','    } else {\n        let misses'),span(b,'let index = if let Some(index) = hit {','    } else {\n        let misses')),
 'generic-final-pin-publication':(a.rsplit('    let slot = &mut parts.slots[index];',1)[1],b.rsplit('    let slot = &mut parts.slots[index];',1)[1]),
 'generic-release-body':(span(a,'pub(crate) fn release<M: CacheMode>','pub(crate) fn pin<M: CacheMode>'),span(b,'pub(crate) fn release<M: CacheMode>','pub(crate) fn pin<M: CacheMode>')),
 'swift-resident-lookup':(span(sa,'    fn resident_lookup(','    fn resident_remove('),span(sb,'    fn resident_lookup(','    fn resident_remove(')),
 'swift-release-body':(span(sa,'    pub(crate) fn release(','    pub(crate) fn cleanup'),span(sb,'    pub(crate) fn release(','    pub(crate) fn cleanup')),
 'swift-cache-pin-wrapper':(span(sa,"impl CacheOperationPhase<'_> {",'    pub(crate) fn complete<T>'),span(sb,"impl CacheOperationPhase<'_> {",'    pub(crate) fn complete<T>')),
}
unchanged={}
for label,(left,right) in checks.items():
 assert left==right,label
 unchanged[label]={'byteIdentical':True,'bytes':len(left.encode()),'sha256':sha(left.encode())}
old=span(a,'            let mut oldest: Option<usize> = None;','            plan[victim] = true;').split('            let victim = oldest',1)[0]
new=span(b,'        let mut oldest: Option<usize> = None;','        oldest.ok_or_else')
normalize=lambda text:''.join(text.replace('parts.slots','slots').split())
assert normalize(old)==normalize(new)
unchanged['frozen-default-victim-loop']={'literalLoopAfterIndentAndPartsReceiverAdaptation':True,'originalEligibilityAndOneCreditPerSlot':True}
sources['preservedBodies']=unchanged
(OUT/'source-seals.json').write_bytes(encoded(sources))
print(json.dumps({'archives':sources,'liveClosureStillMatches':True}))
