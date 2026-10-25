#!/usr/bin/env python3
"""Read-only bounded verification of this retained finite rejection packet."""
import hashlib,json,pathlib,re,tarfile
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[1]
def sha(data):return hashlib.sha256(data).hexdigest()
def read(name):return json.loads((OUT/name).read_text())
source=read('source-seals.json')
for label in ['live-baseline','baseline','candidate']:
 manifest=read(f'{label}-source-manifest.json')
 assert sha((OUT/f'{label}-source-manifest.json').read_bytes())==source[label]['manifestSHA256']
 assert sha((OUT/f'{label}-source.tar.gz').read_bytes())==source[label]['archiveSHA256']
 with tarfile.open(OUT/f'{label}-source.tar.gz','r:gz') as tar:
  members=tar.getmembers();assert len(members)==source[label]['fileCount']
  assert all(m.isfile() and m.name in manifest and not pathlib.PurePosixPath(m.name).is_absolute() and '..' not in pathlib.PurePosixPath(m.name).parts for m in members)
  assert sum(m.size for m in members)==source[label]['sourceBytes']<32*1024*1024
  assert {m.name:sha(tar.extractfile(m).read()) for m in members}==manifest
live=read('live-baseline-source-manifest.json')
assert {name:sha((ROOT/'vm'/name).read_bytes()) for name in live}==live
summary=read('result-summary.json')
assert summary['decision']=='reject-this-candidate-for-live-integration-and-do-not-select-full-target'
assert len(summary['traces'])==6 and all(t['workRatio']>1 for t in summary['traces'])
assert summary['namedInventory']['bytes']==7264 and summary['namedInventory']['fieldCount']==47
assert summary['baselineShape']['fixedBytes']==118240 and summary['candidateShape']['fixedBytes']==118800
expected={'baseline-original-swift':0,'baseline-common':0,'baseline-final-swift':0,'baseline-generic-unit':0,'baseline-generic-integration':0,'candidate-original-swift':101,'candidate-expanded-1':101,'candidate-expanded-2':0,'candidate-generic-unit':0,'candidate-generic-integration':0}
assert {p.name for p in (OUT/'commands').iterdir()}==expected.keys()
for label,code in expected.items():
 p=OUT/'commands'/label;result=json.loads((p/'result.json').read_text());command=json.loads((p/'command.json').read_text())
 assert result['exitCode']==code and result['timedOut'] is False
 assert sha((p/'stdout').read_bytes())==result['stdoutSHA256'] and sha((p/'stderr').read_bytes())==result['stderrSHA256']
 assert sha((p/'source-manifest.json').read_bytes())==command['sourceManifestSHA256']
 assert command['argv'][1]=='test' and '--offline' in command['argv']
 assert command['environmentOverrides']['CARGO_BUILD_JOBS']=='1'
for label,count in [('baseline-original-swift',39),('baseline-final-swift',42),('candidate-expanded-2',49)]:
 assert f'test result: ok. {count} passed; 0 failed;' in (OUT/'commands'/label/'stdout').read_text()
for label,archive in [('baseline-original-swift','live-baseline'),('baseline-final-swift','baseline'),('candidate-expanded-2','candidate')]:
 assert read(f'commands/{label}/source-manifest.json')==read(f'{archive}-source-manifest.json')
for scope in ['generic-unit','generic-integration']:
 norm=lambda t:re.sub(r'finished in [0-9.]+s','finished in <elapsed>s',t)
 assert norm((OUT/'commands'/('baseline-'+scope)/'stdout').read_text())==norm((OUT/'commands'/('candidate-'+scope)/'stdout').read_text())
for path in ['commands/baseline-final-swift/stdout','commands/candidate-expanded-2/stdout']:
 text=(OUT/path).read_text();assert 'COST_HIT work256=2048 allocations=0 decodes=0 evictions=0' in text
 assert 'full_chain_hit_work=260' in text
if (OUT/'cleanup.json').exists():
 assert read('cleanup.json')['removed'] is True and not (OUT/'.scratch').exists()
if (OUT/'seal.json').exists():
 seal=read('seal.json');assert sha((OUT/'seal.json').read_bytes())==(OUT/'seal.sha256').read_text().strip()
 for name,entry in seal['members'].items():
  data=(OUT/name).read_bytes();assert len(data)==entry['bytes'] and sha(data)==entry['sha256'],name
 assert sha((ROOT/'docs/swift-cost-retention-candidate.md').read_bytes())==seal['docSHA256']
print(json.dumps({'verified':True,'decision':'reject','commands':len(expected),'baselineOriginalMethods':39,'baselineWithCommonMethods':42,'candidateMethods':49,'finiteTraces':6,'genericMethodsEach':15,'sourceArchives':3,'liveClosureUnchanged':True,'cleanupRecorded':(OUT/'cleanup.json').exists()}))
