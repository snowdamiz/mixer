from pathlib import Path
import json,hashlib,re,datetime,subprocess,shutil
H=Path(__file__).resolve().parent;R=H.parents[1];P=R/'verification/swift-cache-resident-index';S=H/'owned-scratch'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def save(n,v):(H/n).write_bytes(enc(v))
def read(p):return json.loads(p.read_text())
expected={'seal.json':'fc45e20ca74edc4d435b1d9d82ed8b01bb68a55b42801501901356ab530b39d7','receipt.json':'916b8fdfdc2d78f538bb2fc556a37cce97304850bc4868c8e1685304d2b76267','candidate.patch':'bbf581ceb101f4befbd5d9f837b7fe7648155c36d009b1eb1c46cbc5c3f0401e'}
assert all(sha(P/n)==v for n,v in expected.items())
producer=read(P/'seal.json');assert all(sha(P/n)==v for n,v in producer['members'].items())
b=read(P/'baseline-manifest.json');c=read(P/'candidate-source-manifest.json')
assert all(sha(R/'vm'/n)==v for n,v in b.items())
commands={}
for d in sorted((H/'commands').iterdir()):
 r=read(d/'receipt.json');assert r['sourceUnchanged'] and all(r['streamEOF'].values()) and r['ownedGroupAbsent'] and not r['timedOut'] and r['exitCode']==0
 assert sha(d/'stdout')==r['stdoutSHA256'] and sha(d/'stderr')==r['stderrSHA256'] and sha(d/'source-manifest.json')==r['sourceManifestSHA256']
 m=read(d/'source-manifest.json');original=b if r['cwd'].endswith('/baseline') else c
 changes=[n for n,v in original.items() if m[n]!=v];assert changes in [[],['src/experimental_swift_reactor/cache_tests.rs']]
 counts=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;', (d/'stdout').read_text());assert len(counts)==1
 passed,failed,ignored=map(int,counts[0]);assert failed==0 and ignored==0
 commands[d.name]={'receiptSHA256':sha(d/'receipt.json'),'sourceManifestSHA256':r['sourceManifestSHA256'],'testOnlyOverlay':bool(changes),'testsPassed':passed,'testsIgnored':ignored,'qualifiedCoverage':passed>0,'exitCode':r['exitCode'],'streamEOF':r['streamEOF'],'ownedGroupAbsent':r['ownedGroupAbsent']}
expected_tests={'candidate-cache-debug':29,'candidate-execution':21,'candidate-lifecycle-corrected':49,'candidate-shared-cache':5,'candidate-frozen':1,'baseline-frozen':1,'independent-debug-final':6,'independent-release-final':6,'independent-baseline-final':2}
assert all(commands[n]['testsPassed']==v for n,v in expected_tests.items())
for name in ('independent-debug-final','independent-release-final'):
 text=(H/'commands'/name/'stdout').read_text();assert 'work_prefixes=832 cancellation_checkpoints=852 cleanup=zero' in text and 'work_prefixes=193 cancellation_checkpoints=141 partial_evictions={0, 1, 2, 3, 4} cleanup=zero' in text

def models(n):return [line.split('INDEPENDENT_MODEL ',1)[1] for line in (H/'commands'/n/'stdout').read_text().splitlines() if 'INDEPENDENT_MODEL ' in line]
assert models('independent-debug-final')==models('independent-release-final')==models('independent-baseline-final') and len(models('independent-debug-final'))==4
ps=subprocess.run(['/bin/ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True)
groups=[read(d/'receipt.json')['processGroup'] for d in (H/'commands').iterdir()]
assert not [line for line in ps.stdout.splitlines() if len(line.split())>=2 and int(line.split()[1]) in groups]
(S/'candidate/src/experimental_swift_reactor/cache_tests.rs').exists() or (_ for _ in ()).throw(AssertionError('scratch missing'))
holders=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(S)],capture_output=True)
(H/'cleanup-holder.stdout').write_bytes(holders.stdout);(H/'cleanup-holder.stderr').write_bytes(holders.stderr)
assert holders.returncode==1 and not holders.stdout and not holders.stderr,'scratch holder or failed lsof check'
bytes_owned=sum(x.stat().st_size for x in S.rglob('*') if x.is_file())
shutil.rmtree(S)
save('cleanup.json',{'ownedScratch':str(S),'removed':not S.exists(),'filesBytesRemoved':bytes_owned,'holderCheckArgv':['/usr/sbin/lsof','-nP','+D',str(S)],'holderCheckExitCode':holders.returncode,'holderStdoutSHA256':sha(H/'cleanup-holder.stdout'),'holderStderrSHA256':sha(H/'cleanup-holder.stderr'),'ownedGroupsAbsent':True,'groups':groups,'preservedOtherProjects':True,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat()})
r={'schema':1,'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'assessment':'no-actionable-defect-found-recommend-development-integration','findings':[],'candidateClosure':sha(P/'candidate-source-manifest.json'),'baselineClosure':sha(P/'baseline-manifest.json'),'sourceMembers':132,'producerPacket':expected,'producerMembersVerified':len(producer['members']),'reviewedChangedFiles':read(P/'receipt.json')['changedFiles'],'sourceRevisionAtPreparation':read(H/'packet-audit.json')['rootHEAD'],'sourceRevisionAtSeal':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'commands':commands,'excludedCoverage':{'candidate-lifecycle':'Initial filter selected zero tests; corrected filter passed 49 tests.'},'literalFrozenTraceIdentical':True,'independentModelOperationsPerBuild':8192,'independentDebugReleaseBaselineModelIdentical':True,'constructorWorkPrefixes':832,'constructorCancellationCheckpoints':852,'fourVictimReplacementWorkPrefixes':193,'fourVictimReplacementCancellationCheckpoints':141,'live132BaselineUnchanged':True,'productionLimitsChanged':False,'dependenciesChanged':False,'fullTargetExecuted':False,'fullTargetPassed':False,'nativeOrDeviceExecuted':False,'excludedHostedLanesExecutedOrImported':False,'productionAccepted':False,'gaAccepted':False,'physicalPhoneStatus':'disconnected-deferred','unverified':['full reactor target completion','native iOS Android parity','physical phones','published immutable FieldLog consumption','signing store operational and specified final acceptance gates'],'cleanupSHA256':sha(H/'cleanup.json'),'reportSHA256':sha(R/'docs/swift-cache-resident-index-review.md')}
save('receipt.json',r)
members={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='seal.json'}
save('seal.json',{'schema':1,'candidateClosure':r['candidateClosure'],'producerSealSHA256':sha(P/'seal.json'),'members':members,'membersSHA256':hashlib.sha256(enc(members)).hexdigest(),'receiptSHA256':sha(H/'receipt.json'),'reportPath':'docs/swift-cache-resident-index-review.md','reportSHA256':r['reportSHA256']})
print(json.dumps({'sealed':True,'reviewMembers':len(members),'sealSHA256':sha(H/'seal.json'),'receiptSHA256':sha(H/'receipt.json'),'cleanup':True,'assessment':r['assessment']}))
