import pathlib,json,hashlib,gzip,re,subprocess,datetime
root=pathlib.Path('/Users/andreyyurlov/Documents/dev/mixer');p=root/'verification/swift-calls-dispatch/v7-fixture-expectations';q=p/'qualification/20261024T192400793747Z';out=root/'verification/swift-calls-dispatch-root-review/sealed-v7'
read=lambda f:json.loads(f.read_bytes());sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
r=read(q/'receipt.json');results=read(q/'results.json');plan=read(q/'plan.json');clean=read(q/'independent-cleanup.json');node=read(q/'node-companion-final.json');candidate=read(p/'candidate-final-manifest.json')
assert r['completedCommands']==r['plannedCommands']==len(results)==len(plan)==27 and r['allCommandsPassed'] and r['cleanupComplete']
assert [x['id'] for x in results]==[x['id'] for x in plan] and all(x['exitCode']==0 for x in results)
assert r['selectionSHA256']==sha(root/'verification/swift-calls-dispatch-root-review/v7-runtime-selection.json')=='80069e83a282d6bc35fe21902a3e16286d1fb9e72b680643291438df3fa378ba'
assert r['producerSealSHA256']==sha(p/'review-seal.json')=='79089f1ef382a14e02fbbbf0a6e6dcd0a67158bcfa5354d565a5b037b1d149b2'
assert r['driverSHA256']==sha(q/'driver.py')==sha(p/'qualified_runtime.py')
assert clean['cleanupComplete'] and len(clean['targets'])==27 and len(clean['processes'])==63 and all(x['cleanupComplete'] for x in clean['targets']+clean['processes']) and clean['finalProcessRequery']['allKnownGroupsActuallyEmpty']
assert not clean['recordingErrors'] and all(not pathlib.Path(x['scratch']).exists() for x in clean['targets'])
assert node['allNodePinsPassed'] and node['baseDriverExitCode']==0 and not node['baseDriverRaised'] and node['final']['fullLoaderCacheChecked']
np=read(q/'node-prelaunch-checks.json');assert len(np)==63 and all(x['pinsPassed'] for x in np) and sum(x['ownedOracleArtifact'] for x in np)==4
assert sha(q/'node-companion.py')==sha(root/'verification/swift-calls-dispatch-node-oracle-qualification/companion.py')
test_runs=[];attempts=[]
for row,command in zip(results,plan):
 a=p/row['attempt'];attempts.append(a);assert a.is_relative_to(p/'attempts') and a.is_dir() and not a.is_symlink()
 assert row['sourceClosure']==r['sourceClosure']=='78e2586b41f698c60e1bcd4cdd4abb33fbf98d747d1ee183a793988dea7b5237'
 assert read(a/'source-manifest.json')==candidate
 cmd=read(a/'command.json');assert cmd['argv']==command['argv']
 cleanup=read(a/'cleanup.json');assert cleanup['removed'] and cleanup['holderCheckEmpty'] and not cleanup['remainingGroup'] and not pathlib.Path(cleanup['scratch']).exists()
 if row['id'].startswith(('library-','frozen-')):
  tests=read(a/'test-list.json');assert len(tests)==len(set(tests))
  text=gzip.decompress((a/'execute-stdout.gz').read_bytes()).decode();matches=re.findall(r'^test result: ok\. (\d+) passed; 0 failed; 0 ignored; 0 measured; 0 filtered out;',text,re.M)
  assert matches==[str(len(tests))],row['id']
  test_runs.append({'id':row['id'],'tests':len(tests),'failures':0,'ignored':0,'filtered':0})
  if row['id'].startswith('library-'):
   obs=row['observations'];assert len(obs['cdPrefixes'])==24 and sum(len(v) for v in obs['cdPrefixes'].values())==60 and all(obs['independentExpectedTraces'].values())
assert [v['tests'] for v in test_runs[:4]]==[312,312,342,342] and len(test_runs)==18 and sum(v['tests'] for v in test_runs[4:])==70
f=read(p/'frozen-identity.json');assert len(f['baseline']['methods'])==len(f['candidate']['methods'])==39 and f['baseline']['methods']==f['candidate']['methods']
files={}
for folder in [q,*attempts]:
 for file in sorted(folder.rglob('*')):
  assert not file.is_symlink(),str(file)
  if file.is_file():files[str(file.relative_to(root))]={'sha256':sha(file),'bytes':file.stat().st_size}
for name in ['qualified-runtime.stdout','qualified-runtime.stderr']:
 file=out/name;files[str(file.relative_to(root))]={'sha256':sha(file),'bytes':file.stat().st_size}
report={'schema':'mixer.swift-dispatch.v7-root-runtime-review.1','observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sourceRevisionContext':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),'command':['python3','/tmp/mixer-v7-runtime-review.py'],'reviewerScriptSHA256':sha(pathlib.Path(__file__)),'privateRuntimeAccepted':True,'candidateSourceClosure':r['sourceClosure'],'qualificationDirectory':str(q.relative_to(root)),'selectionSHA256':r['selectionSHA256'],'producerSealSHA256':r['producerSealSHA256'],'plannedAndPassedCommands':27,'sourceAndCompilerPrelaunchChecks':63,'nodePrelaunchChecks':63,'fullOracleArtifactChecks':4,'nodeFinalPinsPassed':True,'testRuns':test_runs,'testExecutions':sum(v['tests'] for v in test_runs),'callDispatchCasesPerLibrary':60,'frozenImplementationMethodsUnchanged':39,'frozenRegressionTestsPerProfile':35,'productionClippyConfigurationsPassed':4,'defaultSpanChecksPassed':4,'newSourcesFormattingPassed':True,'independentCleanup':{'ownedTargetsAbsent':27,'completedProcessGroupsEmpty':63,'nativeInstancesCreated':0},'files':files,'liveProductIntegrated':False,'scope':'Private macOS Rust runtime candidate; host tests and source/tool bindings. No iOS/Android runtime, full Swift readiness, FieldLog, OTA or GA qualification.'}
(out/'runtime-review.json').write_text(json.dumps(report,indent=2)+'\n');(out/'review_runtime.py').write_bytes(pathlib.Path(__file__).read_bytes())
print(json.dumps({k:v for k,v in report.items() if k not in ['files','testRuns']},indent=2));print('artifactCount',len(files),'reviewSHA256',sha(out/'runtime-review.json'))
