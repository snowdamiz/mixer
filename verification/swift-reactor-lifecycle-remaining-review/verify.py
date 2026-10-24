#!/usr/bin/env python3
"""Read-only review replay; no compiler, guest, network or native execution."""
from pathlib import Path
import gzip,hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRODUCER=ROOT/'verification/swift-reactor-lifecycle-remaining-matrix'
PRODUCER_SEAL='90cf6183ffc2d113318cd818631ee98ad436360cdc38acfcda0dcd10fc8e68ce'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def enc(v):return (json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
def verify():
 seal=read(HERE/'seal.json')
 assert {str(p.relative_to(HERE)) for p in HERE.rglob('*') if p.is_file() and p.name!='seal.json'}==set(seal['files'])
 for n,h in seal['files'].items():assert sha(HERE/n)==h,('review seal',n)
 for n,h in seal['externalFiles'].items():assert sha(ROOT/n)==h,('review document',n)
 assert hashlib.sha256(enc(seal['files'])).hexdigest()==seal['filesClosureSHA256']
 assert sha(PRODUCER/'seal.json')==PRODUCER_SEAL
 producer=read(PRODUCER/'seal.json')
 assert {str(p.relative_to(PRODUCER)) for p in PRODUCER.rglob('*') if p.is_file() and p.name!='seal.json'}==set(producer['files'])
 for n,h in producer['files'].items():assert sha(PRODUCER/n)==h,('producer seal',n)
 for n,h in producer['externalFiles'].items():assert sha(ROOT/n)==h,('producer document',n)
 normal=read(HERE/'normal-source-manifest.json');controls=read(HERE/'controls-source-manifest.json')
 assert normal==read(PRODUCER/'candidate-manifest.json') and len(normal)==len(controls)==132
 assert hashlib.sha256(enc(normal)).hexdigest()=='64a3d9c52ade75ec16de10191f14257fb75ff358c366666cf47809e2b9a7f0de'
 name='src/experimental_swift_reactor/lifecycle_tests.rs'
 assert sha(HERE/'normal-lifecycle_tests.rs')==normal[name]
 assert (HERE/'normal-lifecycle_tests.rs').read_bytes()==(PRODUCER/'candidate'/name).read_bytes()
 expected=dict(normal);expected[name]=hashlib.sha256((HERE/'normal-lifecycle_tests.rs').read_bytes()+b'\n'+(HERE/'controls.rs').read_bytes()).hexdigest();assert controls==expected
 baseline=read(HERE/'live-before-manifest.json')
 assert baseline==read(PRODUCER/'baseline-manifest.json')
 assert hashlib.sha256(enc(baseline)).hexdigest()=='93adb6ac2d00acab30c02df8d96e044452edc14d704a6738a58874b0968b5f38'
 # Root may subsequently integrate exactly the reviewed test-only candidate.
 # The recorded audit remains explicitly bound to the prior live baseline.
 current={n:sha(ROOT/'vm'/n) for n in baseline}
 assert current in [baseline,normal], 'unreviewed live source drift'
 audit=read(HERE/'producer-evidence-audit.json')
 assert audit==json.loads((HERE/'commands/independent-sealed-audit-final.stdout').read_text())
 assert audit['verified'] and audit['producerSealSHA256']==PRODUCER_SEAL and audit['qualifiedProducerExecutions']==196 and audit['compilerNegativeExpectedFailures']==6
 results=read(HERE/'independent-results.json')
 for prefix,expected_count,manifest,archive in [('normal',49,normal,'normal-artifact.json'),('controls',2,controls,'controls-artifact.json')]:
  binding=read(HERE/archive);raw=gzip.decompress((HERE/binding['archive']).read_bytes())
  assert hashlib.sha256(raw).hexdigest()==binding['sha256'] and len(raw)==binding['bytes']
  artifact=binding['artifact'];binary=artifact['executable'];assert not artifact['fresh']
  build_label='independent-'+prefix+'-build'
  objects=[json.loads(s) for s in (HERE/'commands'/(build_label+'.stdout')).read_text().splitlines() if s.startswith('{')]
  assert artifact in objects
  listed=(HERE/'commands'/('independent-'+prefix+'-list.stdout')).read_text().splitlines()
  names=[s.removesuffix(': test') for s in listed if s.endswith(': test')]
  assert len(names)==len(set(names))==expected_count
  executed=(HERE/'commands'/('independent-'+prefix+'-execute.stdout')).read_text()
  observed=re.findall(r'^test (\S+) \.\.\. (ok|FAILED|ignored)$',executed,re.M)
  assert observed==[(n,'ok') for n in names]
  assert f'test result: ok. {expected_count} passed; 0 failed; 0 ignored;' in executed
  for suffix in ['build','list','execute']:
   row=read(HERE/'commands'/('independent-'+prefix+'-'+suffix+'.json'));assert row['sourceManifest']==manifest
  assert read(HERE/'commands'/('independent-'+prefix+'-list.json'))['argv']==[binary,'swift_lifecycle_' if prefix=='normal' else 'review_control_','--list','--format','terse']
  assert names==results['normalSelectedIdentities' if prefix=='normal' else 'controlSelectedIdentities']
 commands=[]
 for p in (HERE/'commands').glob('*.json'):
  row=read(p);commands.append(row)
  assert row['sourceManifest'] in [normal,controls]
  assert row['tools']==row['postTools'] and row['sourceUnchanged'] and row['exitCode']==0 and not row['timedOut'] and row['remainingProcessGroup']==[]
  assert row['timeoutSeconds']<=180
  for suffix in ['stdout','stderr']:assert sha(p.with_suffix('.'+suffix))==row[suffix+'SHA256']
 spent=sum(row['durationSeconds'] for row in commands);assert spent<900
 receipt=read(HERE/'receipt.json');assert receipt['recordedCommandSeconds']==spent and receipt['recordedCommands']==len(commands)
 cleanup=read(HERE/'cleanup.json');assert cleanup['ownedTargetRemoved'] and cleanup['ownedSourceCopyRemoved']
 for row in cleanup['ownedPaths']:
  assert row['holderCheckEmpty'] and row['removed'] and not Path(row['path']).exists()
  prefix=Path(row['path']).name
  assert sha(HERE/(prefix+'-holders.stdout'))==row['holderStdoutSHA256']
  assert sha(HERE/(prefix+'-holders.stderr'))==row['holderStderrSHA256']
 assert receipt['blockingFindings']==0 and receipt['completeSLRows']==0 and not receipt['SL24Selected'] and not receipt['newAccountingCredit'] and not receipt['GAaccepted']
 assert read(HERE/'source-review.json')['blockingFindings']==[]
 return {'verified':True,'producerSealedFiles':len(producer['files']),'producerQualifiedExecutions':196,'producerCompilerNegatives':6,'independentNormalPassed':49,'independentControlsPassed':2,'independentControlVariants':8,'completeSLRows':0,'SL24Selected':False,'productionBytesUnchanged':True,'ownedTargetAndSourceRemoved':True,'currentLiveSource':'accepted-baseline' if current==baseline else 'reviewed-test-only-candidate','reviewSealedFiles':len(seal['files'])}
if __name__=='__main__':print(json.dumps(verify(),sort_keys=True))
