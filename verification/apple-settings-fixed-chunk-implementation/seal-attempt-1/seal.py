"""Seal exact source/evidence and archive owned synthetic stores before cleanup."""
import datetime,gzip,hashlib,io,json,pathlib,shutil,stat,tarfile
B=pathlib.Path(__file__).resolve().parent;ROOT=B.parents[1]
DOC=ROOT/'docs/apple-settings-fixed-chunk-implementation.md'
sha=lambda b:hashlib.sha256(b).hexdigest()
def row(p):
 assert p.is_file() and not p.is_symlink(),str(p)
 raw=p.read_bytes();return dict(bytes=len(raw),sha256=sha(raw),mode=stat.S_IMODE(p.stat().st_mode),kind='file')
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def archive(target,items):
 with target.open('wb') as out,gzip.GzipFile(filename='',fileobj=out,mode='wb',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
  for name,p in sorted(items):
   raw=p.read_bytes();info=tarfile.TarInfo(name);info.size=len(raw);info.mode=stat.S_IMODE(p.stat().st_mode);info.mtime=0;info.uid=info.gid=0;tar.addfile(info,io.BytesIO(raw))
def main():
 bindings=json.loads((B/'source-bindings.json').read_bytes())
 for name,value in bindings['derivativeFiles'].items():assert row(B/'sources'/name)['sha256']==value['sha256']
 assert len(bindings['derivativeFiles'])==72
 for name,digest in bindings['inputs'].items():assert row(ROOT/name)['sha256']==digest
 changed=[name for name,value in bindings['derivativeFiles'].items() if value!=bindings['frozenFiles'][name]]
 assert changed==bindings['changedEndpoints'] and len(changed)==2
 source_items=[('docs/apple-settings-fixed-chunk-implementation.md',DOC)]
 for folder in ['sources','inputs','fixture-inputs']:
  source_items += [(str(p.relative_to(B)),p) for p in (B/folder).rglob('*') if p.is_file()]
 source_items += [(p.name,p) for p in B.iterdir() if p.is_file() and p.suffix in ['.py','.swift']]
 source_items += [('source-bindings.json',B/'source-bindings.json')]
 source_manifest={name:row(path) for name,path in source_items}
 (B/'source-package-manifest.json').write_bytes(encoded(source_manifest))
 archive(B/'review-source-package.tar.gz',[('package/'+name,path) for name,path in source_items])
 store_items=[]
 for folder in ['synthetic-attempts','witnesses']:
  store_items += [(str(p.relative_to(B)),p) for p in (B/folder).rglob('*') if p.is_file()]
 evidence={name:row(path) for name,path in store_items}
 (B/'synthetic-evidence-manifest.json').write_bytes(encoded(evidence))
 archive(B/'synthetic-evidence.tar.gz',store_items)
 # Re-read every archived byte before retiring only this lane's owned stores.
 with tarfile.open(B/'synthetic-evidence.tar.gz') as tar:
  members=tar.getmembers();assert len(members)==len(evidence)
  for member in members:
   raw=tar.extractfile(member).read();assert sha(raw)==evidence[member.name]['sha256'] and len(raw)==evidence[member.name]['bytes']
 stores=len(list((B/'synthetic-attempts').iterdir()))
 for folder in ['synthetic-attempts','witnesses']:shutil.rmtree(B/folder)
 controls=json.loads((B/'controls.json').read_bytes());host=json.loads((B/'host-controls.json').read_bytes());commands=json.loads((B/'command-receipt.json').read_bytes())
 assert controls['passed'] and host['passed'] and all(r['exitCode']==0 and r['stdoutEOF'] and r['stderrEOF'] and r['ownedChildReaped'] for r in commands['commands'])
 receipt=dict(schema=1,observedUTC=datetime.datetime.now(datetime.UTC).isoformat(),status='implemented-host-verified-independent-review-pending',sourceRevisionLabel=bindings['sourceRevision'],derivativeSourceTreeSHA256=sha(encoded(bindings['derivativeFiles'])),sourceReviewArchiveSHA256=row(B/'review-source-package.tar.gz')['sha256'],changedEndpointCount=2,unchangedArchivedSources=70,hostMethods=controls['methodsRun'],persistenceCases=len(controls['persistenceControls']),strictProof=next(r for r in controls['fixedFormatControls'] if r['control']=='strict-full-proof'),foundationRows=len(host['serializationRows']),maximumObservedFoundationBodyBytes=max(r['bodyBytes'] for r in host['serializationRows']),syntheticEvidenceFiles=len(evidence),syntheticEvidenceBytes=sum(r['bytes'] for r in evidence.values()),ownedStoresArchivedThenRemoved=stores,ownedWorkingStoresAbsent=all(not (B/f).exists() for f in ['synthetic-attempts','witnesses','owned-host-scratch']),allOwnedChildrenReaped=True,listenersStarted=0,outboundNetworkRequests=0,nativeCommands=0,gitOperations=0,otherProjectsTouched=False,fullUIKitXCTestTypecheck=False,nativeSettingsPassed=False,dependentTabPassed=False,frozenSettingsFailureAndTabSkipRemainAuthoritative=True,physicalPhones='disconnected-deferred',gaAccepted=False)
 (B/'receipt.json').write_bytes(encoded(receipt))
 members={str(DOC.relative_to(ROOT)):row(DOC)}
 for p in sorted(B.rglob('*')):
  if p.is_file() and p not in [B/'handoff.json',B/'verification-result.json']:members[str(p.relative_to(ROOT))]=row(p)
 handoff=dict(schema=1,scope='isolated fixed4992 derivative source and host evidence; independent review pending',members=members,sourceReviewArchiveSHA256=receipt['sourceReviewArchiveSHA256'],nativeAccepted=False,gaAccepted=False,physicalPhones='disconnected-deferred')
 (B/'handoff.json').write_bytes(encoded(handoff))
 print(json.dumps(dict(members=len(members),sourceReviewArchiveSHA256=receipt['sourceReviewArchiveSHA256'],handoffSHA256=sha((B/'handoff.json').read_bytes()),syntheticStoresArchivedRemoved=stores)))
if __name__=='__main__':main()
