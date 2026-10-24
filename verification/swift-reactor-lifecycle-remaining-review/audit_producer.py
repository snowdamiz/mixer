#!/usr/bin/env python3
"""Independent exact-seal, command, inventory, failure and source audit."""
from pathlib import Path
import hashlib,json,gzip,re,datetime
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
B=ROOT/'verification/swift-reactor-lifecycle-remaining-matrix'
SEAL='90cf6183ffc2d113318cd818631ee98ad436360cdc38acfcda0dcd10fc8e68ce'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def enc(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def audit():
 seal=read(B/'seal.json');assert sha(B/'seal.json')==SEAL
 assert {str(p.relative_to(B)) for p in B.rglob('*') if p.is_file() and p.name!='seal.json'}==set(seal['files'])
 for n,h in seal['files'].items():assert sha(B/n)==h,n
 for n,h in seal['externalFiles'].items():assert sha(ROOT/n)==h,n
 candidate=read(B/'candidate-manifest.json');baseline=read(B/'baseline-manifest.json')
 assert candidate==read(HERE/'normal-source-manifest.json')
 assert len(candidate)==len(baseline)==132
 assert hashlib.sha256(enc(baseline)).hexdigest()=='93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38'
 assert hashlib.sha256(enc(candidate)).hexdigest()=='64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de'
 assert all(sha(ROOT/'vm'/n)==h for n,h in baseline.items())
 assert {str(p.relative_to(B/'candidate')):sha(p) for p in (B/'candidate').rglob('*') if p.is_file()}==candidate
 changes=sorted(n for n in candidate if candidate[n]!=baseline[n]);assert changes==['src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/memory_growth_operations_tests.rs']
 binding=read(B/'baseline.json')
 for n,h in binding['directEvidenceReferences'].items():assert sha(ROOT/n)==h,n
 alltests=None;execution_count=0
 configs=read(B/'configuration-results.json')
 assert {c['configuration'] for c in configs}=={'swift-debug','all-debug','swift-release','all-release'}
 for c in configs:
  archive=B/c['archive'];assert sha(archive)==c['archiveSHA256'];raw=gzip.decompress(archive.read_bytes());assert hashlib.sha256(raw).hexdigest()==c['executableSHA256']
  names=c['listed'];assert len(names)==len(set(names))==49 and c['ignored']==[]
  assert set(names)==set(c['passed'])
  if alltests is None:alltests=set(names)
  assert alltests==set(names)
  assert read(B/'prior-test-inventory.json')==read(ROOT/'verification/swift-reactor-lifecycle-v3-integration/exact-tests.json')
  assert set(read(B/'prior-test-inventory.json'))<=set(names)
  flags={'swift-debug':['--features','experimental-swift-reactor'],'all-debug':['--all-features'],'swift-release':['--features','experimental-swift-reactor','--release'],'all-release':['--all-features','--release']}[c['configuration']]
  expected_build=['cargo','test','--lib','--locked','--offline','--no-default-features',*flags,'--no-run','--message-format=json-render-diagnostics']
  assert read(B/'commands'/(c['commands'][0]+'.json'))['argv']==expected_build
  assert read(B/'commands'/(c['commands'][1]+'.json'))['argv']==[c['executablePath'],'swift_lifecycle_','--list','--format','terse']
  assert read(B/'commands'/(c['commands'][2]+'.json'))['argv']==[c['executablePath'],'swift_lifecycle_','--test-threads=1']
  for label in c['commands']:
   row=read(B/'commands'/(label+'.json'));assert row['candidateManifest']==candidate and row['exitCode']==0 and not row['timedOut'] and row['sourceUnchanged'] and row['tools']==row['postTools']
  objects=[json.loads(s) for s in (B/'commands'/(c['commands'][0]+'.stdout')).read_text().splitlines() if s.startswith('{')]
  assert c['artifact'] in objects and c['artifact']['executable']==c['executablePath'] and not c['artifact']['fresh']
  listlines=(B/'commands'/(c['commands'][1]+'.stdout')).read_text().splitlines()
  assert [s.removesuffix(': test') for s in listlines if s.endswith(': test')]==names
  execute=(B/'commands'/(c['commands'][2]+'.stdout')).read_text()
  statuses=re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)$',execute,re.M)
  assert len(statuses)==49 and dict(statuses)=={n:'ok' for n in names}
  assert re.search(r'test result: ok\. 49 passed; 0 failed; 0 ignored; 0 measured;',execute)
  execution_count+=len(statuses)
 assert execution_count==196
 negatives=read(B/'negative-results.json');assert len(negatives)==6
 for row in negatives:
  cmd=read(B/'commands'/(row['command']+'.json'));assert cmd['exitCode']==1 and not cmd['timedOut'] and cmd['sourceUnchanged']
  actual=[json.loads(s) for s in (B/'commands'/(row['command']+'.stderr')).read_text().splitlines() if s.startswith('{')]
  assert all(d in actual for d in row['matchedDiagnostics'])
  assert row['matchedDiagnostics'] and all(d['code']['code']==row['expectedCode'] for d in row['matchedDiagnostics'])
  assert row['expectedCode']=={'external-construction':'E0603','external-forged-request':'E0603','external-pin-escape':'E0603','external-arbitrary-invocation':'E0425','whole-owner':'E0506','retained-owner':'E0506'}[row['case']]
  if row['case'] in ['whole-owner','retained-owner']:
   assert all(any(s['is_primary'] and s['text'][0]['text'].strip()=='owner.lifecycle = Lifecycle::Ready;' for s in d['spans']) for d in row['matchedDiagnostics'])
   name=row['case'].replace('-','_');injected=B/'negative'/(name+'-injected-lifecycle_tests.rs')
   assert injected.read_bytes()==(B/'candidate/src/experimental_swift_reactor/lifecycle_tests.rs').read_bytes()+b'\n'+(B/'negative'/(name+'.rs')).read_bytes()
   assert sha(injected)==cmd['compilerNegativeManifest']['src/experimental_swift_reactor/lifecycle_tests.rs']
   assert cmd['compilerNegativeSourceUnchanged']
 ledger=read(B/'coverage-ledger.json');rows=ledger['rows']
 assert [r['id'] for r in rows]==[f'SL{i:02}' for i in range(1,25)]
 assert all(r['status']=='partial' and r['complete']==False and r['remaining'] for r in rows[:23])
 assert rows[23]['status']=='not-selected' and rows[23]['selectedTests']==[]
 assert {name for r in rows for name in r['selectedTests']}=={name.rsplit('::',1)[-1] for name in alltests}
 commands=[read(p) for p in (B/'commands').glob('*.json')]
 for p in (B/'commands').glob('*.json'):
  row=read(p)
  for suffix in ['stdout','stderr']:assert sha(p.with_suffix('.'+suffix))==row[suffix+'SHA256']
  assert row['timeoutSeconds']<=180 and not row['timedOut'] and row['sourceUnchanged'] and row['remainingProcessGroup']==[]
  assert row['tools']==row['postTools']
 assert sum(c['durationSeconds'] for c in commands)<1800
 history=read(B/'failure-history.json')
 for row in history['preservedFailures']:
  command=read(B/'commands'/(row['command']+'.json'));assert command['exitCode']!=0
  if 'sourceSnapshot' in row:
   source=B/row['sourceSnapshot'];assert command['candidateManifest']['src/experimental_swift_reactor/lifecycle_tests.rs']==sha(source)
  else:
   assert row['command']=='negative-external-construction'
   error=(B/'commands/negative-external-construction.stderr').read_text()
   assert 'E0463' in error and 'unknown' in error
 for label in ['swift-debug-execute','swift-debug-execute-v3']:
  assert 'FAILED' in (B/'commands'/(label+'.stdout')).read_text()
 cleanup=read(B/'cleanup.json');assert cleanup['exitCode']==1 and cleanup['liveHolders']==[] and not (B/'owned-target').exists() and (B/'cleanup-holders.stdout').read_bytes()==b''
 source=(B/'candidate/src/experimental_swift_reactor/lifecycle_tests.rs').read_text()
 assert 'allow(unexpected_cfgs)' not in source and 'remaining-matrix-whole-owner-negative' not in source and 'remaining-matrix-retained-owner-negative' not in source
 return {'observedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verified':True,'producerSealSHA256':sha(B/'seal.json'),'producerSealedFiles':len(seal['files']),'normalSourceMatchesReviewCopy':True,'allProductionBytesExact':True,'changedPaths':changes,'qualifiedProducerExecutions':execution_count,'exactSelectedIdentities':len(alltests),'preservedPriorIdentities':23,'newIdentities':26,'compilerNegativeExpectedFailures':6,'allCommandHashesAndStableToolsVerified':True,'completeSLRows':0,'SL24Selected':False,'priorFailedAttemptsSourceBound':True,'cleanupVerified':True,'producerCommandSeconds':sum(c['durationSeconds'] for c in commands)}
if __name__=='__main__':print(json.dumps(audit(),indent=2,sort_keys=True))
