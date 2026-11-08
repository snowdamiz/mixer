from pathlib import Path
import datetime,difflib,hashlib,importlib.util,json,os,shutil,sys,time
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;ROOT=O.parents[2];P=O.parent;S=O/'candidate';C=P/'store-credential-index-campaign';V=P/'store-credential-index-review'
base='96f03ab65966a6374e958e780fa09a3eed814c0b'
paths=['cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift','cli/Sources/MixerBuild/StoreReconciliation.swift','cli/Sources/MixerCLI/main.swift','cli/Tests/MixerBuildTests/StoreReconciliationTests.swift']
def sha(b):return hashlib.sha256(b).hexdigest()
def h(p):return sha(p.read_bytes())
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def hashes(root):return {str(p.relative_to(root)):h(p) for p in sorted(root.rglob('*')) if p.is_file()}
state=json.loads((O/'state.json').read_text());n=state['attempts'];final=json.loads((O/f'attempt-{n}/receipt.json').read_text())
assert n<=2 and final['passed'] and final['sourceStable'] and final['cleanup']['allTerminalCustody'] and not final['cleanup']['hold']
source=hashes(S);assert source==final['sourceHashes'] and len(source)==116
assert h(O/'cleanup_control.py')==h(P/'native-custody-premise/cleanup_control.py')=='8885f85a8d49ffbce813dd4221dc381ca88feef98f0f3905e67f4610381365df'
b=json.loads((O/'protected-baseline.json').read_text())
post={'owning101':{p:h(ROOT/p)==v['sha256'] for p,v in b['owning'].items()},'canonicalFour':{p:(h(ROOT/p) if (ROOT/p).exists() else None)==v['base'] for p,v in b['canonical'].items()},'campaign116':{p:h(C/'candidate'/p)==v for p,v in b['candidate'].items()},'campaignEvidence':{p:h(C/p)==v for p,v in b['campaignEvidence'].items()},'preservedFailureReferences':{p:h(P/p)==v for p,v in b['failureReferences'].items()},'final116Frozen':source==final['sourceHashes'],'sourceDigest':sha(json.dumps(source,sort_keys=True,separators=(',',':')).encode()),'owningInputDigest':'a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'}
assert all(all(post[k].values()) for k in ['owning101','canonicalFour','campaign116','campaignEvidence','preservedFailureReferences'])
A=O/'packaging';A.mkdir();scratch=A/'scratch';scratch.mkdir()
env={k:os.environ[k] for k in ['PATH','HOME','USER','LOGNAME','LANG','LC_ALL','SHELL'] if k in os.environ};env['TMPDIR']=str(scratch)+'/'
spec=importlib.util.spec_from_file_location('custody',O/'cleanup_control.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
c=m.Commands(A,env,deadline=time.monotonic()+min(60,state['deadline']-time.time()),cleanup_seconds=5,output_bytes=4194304,total_output_bytes=33554432-state['usedOutput'])
try:
 post['HEAD']=c.run('head',['git','rev-parse','HEAD'],ROOT)
 assert post['HEAD']=='62ce9b76840b2fa56306736fc4c4fe2962780adf'
 basefiles={}
 for i,p in enumerate(paths):
  c.run('base-file-'+str(i),['git','show',base+':'+p],ROOT,allowed=(0,128))
  record=c.records[-1];basefiles[p]=Path(record['logs']['stdout']).read_bytes() if record['exit_code']==0 else None
 def patch(before):
  parts=[]
  for p in paths:
   old=before[p];new=(S/p).read_bytes()
   if old==new:continue
   parts.append(f'diff --git a/{p} b/{p}\n')
   if old is None:parts.append('new file mode 100644\n')
   parts.extend(difflib.unified_diff((old or b'').decode().splitlines(True),new.decode().splitlines(True),fromfile='/dev/null' if old is None else 'a/'+p,tofile='b/'+p))
  return ''.join(parts).encode()
 (O/'implementation.patch').write_bytes(patch(basefiles))
 campaign={p:(C/'candidate'/p).read_bytes() for p in paths}
 (O/'campaign-increment.patch').write_bytes(patch(campaign))
 for label,before,patchname in [('full',basefiles,'implementation.patch'),('incremental',campaign,'campaign-increment.patch')]:
  check=scratch/label;check.mkdir()
  for p,data in before.items():
   if data is not None:
    target=check/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  for flags in [['--check'],[]]:
   c.run('apply-'+label+str(len(flags)),['git','apply',*flags,'--directory='+str(check.relative_to(ROOT)),O/patchname],ROOT)
  assert all((check/p).read_bytes()==(S/p).read_bytes() for p in paths)
 old=(C/'candidate'/paths[3]).read_text();new=(S/paths[3]).read_text()
 fixture='let pending = Data(("mixer-credential-v1\\n\\(future.utf8.count)-\\(digest)\\n").utf8)'
 expected=old.replace(fixture,'let pending = reviewPendingData(future)')
 r3=(P/'store-status-fix-r3/candidate'/paths[3]).read_text()
 a=r3.index('    @Test func recognizedCredentialIsRemovedBefore401AndMissingToken()');z=r3.index('    private func compact(',a);e=r3.index('    @Test func processingStatesAndRepeatedInvocationPreserveVersionWithoutReadiness()')
 independent=(V/'source/cli/Tests/MixerBuildTests/StoreCredentialIndependentTests.swift').read_text()
 port=new[new.index('private let reviewIdentity'):new.index('\nprivate func reviewIndexSnapshot')].rstrip()+'\n'
 preservation={'supplied23AndHelpersExceptOnePendingFixture':new.startswith(expected+'\n'),'originalEightAndTrailingHelpers':r3[e:] in new,'r2FourSecurityGroups':r3[a:z] in new,'originalSharedHelpersExceptDarwinImport':r3[:r3.index('@Suite(.serialized)')] in new,'readerAndCLIUnchangedFromCampaign':all((S/p).read_bytes()==campaign[p] for p in [paths[0],paths[2]]),'fivePassingIndependentBodiesUnchanged':independent[independent.index('    @Test func independentMembership'):].rstrip() in port,'sixIndependentGroupsRetained':port.count('@Test func')==6,'totalGroups':new.count('@Test func'),'productFileCount':4}
 assert all(v for k,v in preservation.items()) and preservation['totalGroups']==31
 save(O/'preservation.json',preservation)
 (O/'independent-port.patch').write_text(''.join(difflib.unified_diff(independent.splitlines(True),(independent[:independent.index('private let reviewIdentity')]+port).splitlines(True),fromfile='review/StoreCredentialIndependentTests.swift',tofile='ported-into/StoreReconciliationTests.swift')))
 attempts=[]
 for i in range(1,n+1):
  ar=O/f'attempt-{i}';r=json.loads((ar/'receipt.json').read_text());log=Path(r['commands'][-1]['logs']['stdout']).read_text()
  assert all(h(ar/p)==v for p,v in r['logHashes'].items())
  attempts.append({'attempt':i,'receiptSHA256':h(ar/'receipt.json'),'sourceDigest':r['sourceDigest'],'sourceStable':r['sourceStable'],'passed':r['passed'],'testGroups':sum(x.startswith('◇ Test ') and not x.startswith('◇ Test run') for x in log.splitlines()),'passedGroups':sum(x.startswith('✔ Test ') and not x.startswith('✔ Test run') for x in log.splitlines()),'logHashes':r['logHashes'],'cleanup':r['cleanup'],'peakScratchBytes':r['peakScratch']})
 assert attempts[-1]['testGroups']==31 and attempts[-1]['passedGroups']==31
 manifest={'base':base,'parentHEAD':post['HEAD'],'candidateOnly':True,'independentlyAccepted':False,'status':'31 serialized host test groups passed; fresh independent review, integration, source-103 and six actual consumers pending','fileCount':4,'additionalIndependentProductFile':False,'independentTestsPlacement':'All six independent groups and their helpers merged into existing StoreReconciliationTests.swift; no fifth path or 117th input','files':{p:{'sha256':h(S/p),'bytes':(S/p).stat().st_size} for p in paths},'patches':{name:{'sha256':h(O/name),'bytes':(O/name).stat().st_size} for name in ['implementation.patch','campaign-increment.patch','independent-port.patch','attempt-1-fixture-correction.patch']},'sourceCount':116,'finalSourceDigest':post['sourceDigest'],'finalSourceHashes':source,'campaignSourceDigest':'a188d2391aa55b5301c85d8c40836a9e07832420bd98b642d93592bdfaf06088','campaignFullPatchSHA256':'25085ad55e7d18c86333bdf1d0faf64cfd7ef3f944a292522d49169a0d488c77','pendingFormat':'mixer-credential-v2\\n<canonical 1...256 decimal length>-<64 lowercase hex fingerprint>\\n<64 lowercase hex SHA256 of all preceding bytes>\\n','maximumPendingBytes':154,'legacyPendingBehavior':'Any present unchecked v1 or unknown version refuses with store.credential-index and preserves pending, roots, nodes and prior record; no automatic checksum conversion. Legitimate R1 and unexhausted R2 record migration remains accepted; exhausted R2 remains refused.','checks':preservation|{'fullPatchAppliesAndMatches':True,'incrementalPatchAppliesAndMatches':True},'attempts':attempts,'preservedFailureReferences':b['failureReferences'],'preservedCampaignEvidence':b['campaignEvidence'],'tool':{'swiftExecutable':final['commands'][-1]['argv'][0],'swiftSHA256':final['swiftSHA256'],'versionReceipt':'attempt-1/receipt.json','custodyControllerSHA256':h(O/'cleanup_control.py')},'scope':'Offline macOS host synthetic credential tests. No live provider, native/UI/device/AX, child agent, credentials, commit, push, held actions, canonical integration, actual consumers or GA claim.'}
 save(O/'patch-manifest.json',manifest)
 save(O/'source-hashes.json',source)
 post['final116FrozenAfterPackaging']=hashes(S)==source
finally:
 post['packagingEnvironment']=env;post['cleanup']=c.cleanup(scratch);post['aggregateManagedOutputBytes']=state['usedOutput']+c.used_output
 post['packagingLogHashes']={p.name:h(p) for p in A.iterdir() if p.suffix in ['.stdout','.stderr']}
 post['elapsedSeconds']=time.time()-state['started'];post['recordedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 save(O/'postflight.json',post)
assert post['cleanup']['allTerminalCustody'] and post['cleanup']['scratchRemoved']
print(json.dumps({'files':manifest['files'],'patches':manifest['patches'],'finalSourceDigest':manifest['finalSourceDigest'],'cleanup':post['cleanup'],'elapsedSeconds':post['elapsedSeconds']},indent=2))
