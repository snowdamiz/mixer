from pathlib import Path
import datetime,hashlib,importlib.util,json,os,sys,time
sys.dont_write_bytecode=True
O=Path(__file__).resolve().parent;ROOT=O.parents[2];P=O.parent;F=P/'store-journal-integrity-fix';C=P/'store-credential-index-campaign';V=P/'store-credential-index-review'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,j):p.write_text(json.dumps(j,sort_keys=True,indent=2)+'\n')
r=json.loads((O/'attempt-1/receipt.json').read_text());b=json.loads((F/'protected-baseline.json').read_text());m=json.loads((F/'patch-manifest.json').read_text())
assert r['passed'] and r['sourceStable'] and r['cleanup']['allTerminalCustody'] and r['cleanup']['scratchRemoved'] and all(r['protectedPostflight'].values())
protected=json.loads((O/'protected-baseline.json').read_text());checks={p:(h(ROOT/p) if (ROOT/p).exists() else None)==digest for p,digest in protected.items()}
assert all(checks.values())
original=json.loads((F/'source-hashes.json').read_text());tested=json.loads((O/'attempt-1/source-hashes.json').read_text())
test='cli/Tests/MixerBuildTests/StoreReconciliationTests.swift';old=(C/'candidate'/test).read_text();new=(F/'candidate'/test).read_text();r3=(P/'store-status-fix-r3/candidate'/test).read_text();independent=(V/'source/cli/Tests/MixerBuildTests/StoreCredentialIndependentTests.swift').read_text()
fixture='let pending = Data(("mixer-credential-v1\\n\\(future.utf8.count)-\\(digest)\\n").utf8)'
expected=old.replace(fixture,'let pending = reviewPendingData(future)');assert expected!=old
start=r3.index('    @Test func recognizedCredentialIsRemovedBefore401AndMissingToken()');end=r3.index('    private func compact(',start);last=r3.index('    @Test func processingStatesAndRepeatedInvocationPreserveVersionWithoutReadiness()')
port=new[new.index('private let reviewIdentity'):new.index('\nprivate func reviewIndexSnapshot')].rstrip()+'\n'
preservation={'supplied23ExceptPendingFixture':new.startswith(expected+'\n'),'originalEightAndTrailingHelpers':r3[last:] in new,'r2FourSecurityGroups':r3[start:end] in new,'originalHelpersExceptDarwinImport':r3[:r3.index('@Suite(.serialized)')] in new,'fivePassingIndependentBodies':independent[independent.index('    @Test func independentMembership'):].rstrip() in port,'sixIndependentGroups':port.count('@Test func')==6,'supplied31ExactPrefixInFreshRun':(O/'source'/test).read_bytes()==(F/'candidate'/test).read_bytes()+(O/'independent-probes.swift').read_bytes(),'originalProductionAndOtherInputsExact':all(tested[p]==digest for p,digest in original.items() if p!=test),'readerAndCLIUnchanged':all((F/'candidate'/p).read_bytes()==(C/'candidate'/p).read_bytes() for p in ['cli/Sources/MixerBuild/AppStoreConnectBuildStatus.swift','cli/Sources/MixerCLI/main.swift'])}
assert all(preservation.values())
a1=json.loads((F/'attempt-1/source-hashes.json').read_text());a2=json.loads((F/'attempt-2/source-hashes.json').read_text());assert a2==original and [p for p in a1 if a1[p]!=a2[p]]==[test]
digest=hashlib.sha256()
for path,info in sorted(b['owning'].items()):
 assert h(ROOT/path)==info['sha256'];digest.update((path+'\0'+info['sha256']+'\n').encode())
assert digest.hexdigest()=='a10a62cc79145bc80bfd780257589f437cc82e2f1ebaad6ccde39c134d56e0ca'
stdout=Path(r['commands'][-1]['logs']['stdout']).read_text();assert '33 tests in 1 suite passed after 8.094 seconds' in stdout
assert all(h(O/'attempt-1'/p)==digest for p,digest in r['logHashes'].items())
result={'verdict':'ACCEPT','scope':'Parent four-path integration, source-103 rebind and actual six-consumer execution may proceed; none performed by this reviewer.','recordedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protected404':checks,'preservation':preservation,'owningInputCount':len(b['owning']),'owningInputDigest':digest.hexdigest(),'candidateSourceDigest':r['candidateDigest'],'testedSourceDigest':r['sourceDigest'],'receiptSHA256':h(O/'attempt-1/receipt.json'),'freshProbesSHA256':h(O/'independent-probes.swift'),'testSourceSHA256':h(O/'source'/test),'groups':33,'testSeconds':8.094,'freshEveryByteRefusals':462,'freshStatusRefusals':20,'suppliedLayoutRefusals':90,'originalCorruptionOraclePassed':True,'patches':m['patches'],'files':m['files'],'correctionAttemptOnlyTestChanged':True,'priorFailuresPreserved':True,'testCleanup':r['cleanup'],'peakScratchBytes':r['peakScratch'],'testLogHashes':r['logHashes'],'runtimeScope':'macOS host synthetic tests only, dependency egress uninstrumented','holdsReleased':False}
# digest above is not reused as a loop variable outside its comprehension on Python 3.
A=O/'final-control';A.mkdir();scratch=A/'scratch';scratch.mkdir()
env=dict(r['environment']);env['TMPDIR']=str(scratch)+'/'
spec=importlib.util.spec_from_file_location('custody',O/'cleanup_control.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
c=module.Commands(A,env,deadline=time.monotonic()+30,output_bytes=4194304,total_output_bytes=33554432-r['cleanup']['aggregateBytes'],cleanup_seconds=5)
try:
 result['HEAD']=c.run('head',['git','rev-parse','HEAD'],ROOT);assert result['HEAD']=='62ce9b76840b2fa56306736fc4c4fe2962780adf'
 result['baseToHeadPaths']=c.run('base-to-head',['git','diff','--name-only',m['base'],result['HEAD']],ROOT).splitlines()
finally:
 result['finalEnvironment']=env;result['finalCleanup']=c.cleanup(scratch);result['aggregateManagedOutputBytes']=r['cleanup']['aggregateBytes']+c.used_output
 result['finalCommandLogHashes']={p.name:h(p) for p in A.iterdir() if p.suffix in ['.stdout','.stderr']}
 result['protectedStillExact']=all((h(ROOT/p) if (ROOT/p).exists() else None)==d for p,d in protected.items())
 save(O/'postflight.json',result)
assert result['finalCleanup']['allTerminalCustody'] and result['finalCleanup']['scratchRemoved'] and result['protectedStillExact']
print(json.dumps({k:result[k] for k in ['verdict','HEAD','groups','testSeconds','receiptSHA256','testSourceSHA256','freshProbesSHA256','aggregateManagedOutputBytes','owningInputDigest','finalCleanup']}))
