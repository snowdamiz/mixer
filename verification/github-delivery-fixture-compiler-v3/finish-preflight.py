import hashlib,json,platform
from owned import OUT,ROOT,row,save,now
s=json.loads((OUT/'selection.json').read_bytes())
save('preflight-initial-failure.json',{'at':now(),'failure':'Protected store path typed as artifacts/store.ex; actual browser_auth/store.ex verified in continuation','completedGitGhCommands':8,'commandsReplayed':False,'productOrCompilerStarted':False})
commands=[]
for p in sorted(OUT.glob('preflight-*.command.json')):
 r=json.loads(p.read_bytes());assert r['exit']==0 and r['stopReason'] is None and all(r[k] for k in ('directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF'))
 commands.append({'name':p.name,**{k:r[k] for k in ('exit','stopReason','directChildReaped','ownedGroupAbsent','stdoutEOF','stderrEOF')}})
raw=(OUT/'preflight-dependency-index.stdout').read_bytes();bindings=[]
for item in raw.split(b'\0'):
 if item:
  meta,path=item.decode().split('\t');mode,oid,stage=meta.split();b=(ROOT/path).read_bytes();assert stage=='0' and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==oid
  bindings.append({**row(ROOT/path),'gitBlob':oid})
protected={'.github/workflows/hosted.yml':'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57','hosted/lib/mixer_hosted/browser_auth/store.ex':'8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299'}
for p,h in protected.items():assert row(ROOT/p)['sha256']==h,p
assert row(OUT/'fieldlog-parent-sid-result.json')==s['fieldlogLatest']
save('dependency-bindings.json',{'schema':1,'at':now(),'base':s['base'],'members':bindings,'trackedMembers':len(bindings),'basePackDuplicated':False,'oldV2AndWorkflowUnchanged':True})
save('preflight.json',{'schema':1,'at':now(),'base':s['base'],'baseTree':s['baseTree'],'candidateSeal':row(ROOT/'verification/cache-fixture-compiler-admission-v3/seal.json'),'dependencyBinding':row(OUT/'dependency-bindings.json'),'versions':{x:(OUT/('preflight-'+x+'-version.stdout')).read_text().strip() for x in ('git','gh')},'python':platform.python_version(),'protectedFiles':protected,'allCommands':commands,'allCommandsReapedGroupsAbsentAndEOF':True,'initialPathTypoCorrectedWithoutCommandReplay':True,'localCompilerRustSwiftElixirRuntimeNativeUICaptureInventoryOrHeldProbeStarted':False})
print(json.dumps({'preflight':'passed','trackedDependencies':len(bindings),'commands':len(commands)}))
