#!/usr/bin/env python3
"""Read-only exact packet replay: does not compile, execute guests or allocate authority."""
import gzip,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(name):return json.loads((HERE/name).read_text())
def encoded(value):return (json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
def manifest(tree):return {str(p.relative_to(tree)):sha(p.read_bytes()) for p in sorted(tree.rglob('*')) if p.is_file()}
def verify():
 seal=read('seal.json')
 for name,pin in seal['files'].items():
  assert sha((HERE/name).read_bytes())==pin,('seal',name)
 for name,pin in seal['externalFiles'].items():
  assert sha((ROOT/name).read_bytes())==pin,('external seal',name)
 actual={str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json'}
 assert actual==set(seal['files']),('unexpected or missing packet member',actual^set(seal['files']))
 baseline=read('baseline-manifest.json'); binding=read('baseline.json');candidate=read('candidate-manifest.json');receipt=read('receipt.json')
 assert len(baseline)==len(candidate)==132
 assert sha(encoded(baseline))==binding['acceptedProductionClosure']=='93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38'
 assert sha(encoded(candidate))==receipt['candidateClosure']=='64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de'
 assert manifest(HERE/'candidate')==candidate
 assert set(n for n in candidate if candidate[n]!=baseline[n])==set(receipt['changedFiles'])=={'src/experimental_swift_reactor/lifecycle_tests.rs','src/experimental_swift_reactor/cache_tests.rs','src/experimental_swift_reactor/memory_growth_operations_tests.rs'}
 for name,pin in baseline.items(): assert sha((ROOT/'vm'/name).read_bytes())==pin,('live baseline drift',name)
 for name,pin in binding['directEvidenceReferences'].items(): assert sha((ROOT/name).read_bytes())==pin,('reference drift',name)
 source=(HERE/'candidate/src/experimental_swift_reactor/lifecycle_tests.rs').read_text()
 assert 'allow(unexpected_cfgs)' not in source and 'remaining-matrix-whole-owner-negative' not in source and 'remaining-matrix-retained-owner-negative' not in source
 selected=sorted(re.findall(r'^fn (swift_lifecycle_\w+)\(',source,re.M));assert len(selected)==49
 prior=read('prior-test-inventory.json');assert len(prior)==23
 configs=read('configuration-results.json');assert {c['configuration'] for c in configs}=={'swift-debug','all-debug','swift-release','all-release'}
 for config in configs:
  assert len(config['passed'])==49 and not config['ignored']
  assert sorted(config['passed'])==sorted(config['listed'])
  assert sorted(x.rsplit('::',1)[-1] for x in config['listed'])==selected
  assert set(prior)<=set(config['listed'])
  raw=(HERE/config['archive']).read_bytes();assert sha(raw)==config['archiveSHA256'] and sha(gzip.decompress(raw))==config['executableSHA256']
  for command in config['commands']:
   row=read('commands/'+command+'.json');assert row['exitCode']==0 and row['candidateManifest']==candidate
  output=(HERE/'commands'/(config['commands'][2]+'.stdout')).read_text()
  assert sorted(re.findall(r'^test (\S+) \.\.\. ok$',output,re.M))==sorted(config['listed'])
  assert 'test result: ok. 49 passed; 0 failed; 0 ignored;' in output
 negatives=read('negative-results.json');assert len(negatives)==6
 for case in negatives:
  command=read('commands/'+case['command']+'.json');assert command['exitCode']==1 and command['sourceUnchanged']
  diagnostics=[json.loads(line) for line in (HERE/'commands'/(case['command']+'.stderr')).read_text().splitlines() if line.startswith('{')]
  assert case['matchedDiagnostics'] and all(d in diagnostics and d['code']['code']==case['expectedCode'] for d in case['matchedDiagnostics'])
  if case['case'] in ['whole-owner','retained-owner']:
   assert command['compilerNegativeSourceUnchanged']
   name=case['case'].replace('-','_');fixture=(HERE/'negative'/(name+'.rs')).read_bytes();injected=(HERE/'negative'/(name+'-injected-lifecycle_tests.rs')).read_bytes()
   assert injected==(HERE/'candidate/src/experimental_swift_reactor/lifecycle_tests.rs').read_bytes()+b'\n'+fixture
   assert sha(injected)==command['compilerNegativeManifest']['src/experimental_swift_reactor/lifecycle_tests.rs']
 commands=[json.loads(p.read_text()) for p in (HERE/'commands').glob('*.json')]
 assert sum(row['durationSeconds'] for row in commands)<1800
 assert all(row['timeoutSeconds']<=180 and not row['timedOut'] and not row['remainingProcessGroup'] and row['sourceUnchanged'] for row in commands)
 for file in (HERE/'commands').glob('*.json'):
  row=json.loads(file.read_text())
  for suffix in ['stdout','stderr']:
   assert sha(file.with_suffix('.'+suffix).read_bytes())==row[suffix+'SHA256']
 cleanup=read('cleanup.json');assert cleanup['targetAbsent'] and not cleanup['liveHolders'] and not (HERE/'owned-target').exists()
 ledger=read('coverage-ledger.json');assert ledger['fullSLRowsComplete']==0 and not ledger['accountingCreditAdded']
 assert len(ledger['rows'])==24 and all(not row['complete'] and row['remaining'] for row in ledger['rows'])
 assert all(row['status']=='partial' for row in ledger['rows'][:23]) and ledger['rows'][23]['status']=='not-selected'
 assert read('commands/final-rustfmt-check.json')['exitCode']==0
 print(json.dumps({'verified':True,'qualifiedExecutions':196,'negativeFixtures':6,'fullSLRowsComplete':0,'ownedTargetRemoved':True,'sourceFiles':132,'productionEngineBytesUnchanged':True,'sealedFiles':len(seal['files'])},sort_keys=True))
if __name__=='__main__':verify()
