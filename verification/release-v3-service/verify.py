#!/usr/bin/env python3
"""Run only after source review: immutable export and scoped service-v3 evidence."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2];OWN=ROOT/'verification/release-v3-service'
p=argparse.ArgumentParser();p.add_argument('--name',required=True);a=p.parse_args();assert re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',a.name)
out=OWN/a.name;out.mkdir(exist_ok=False);source=ROOT/'.build/release-v3-service'/a.name/'source';source.mkdir(parents=True,exist_ok=False)
sha=lambda b:hashlib.sha256(b).hexdigest();digest=lambda p:sha(p.read_bytes())
def inputs():
 paths=[ROOT/'contracts/release-v2.json',ROOT/'services/go.mod',ROOT/'services/go.sum',ROOT/'services/README.md',ROOT/'services/verification/postgres.py',ROOT/'docs/release-v3-service-design.md',Path(__file__),OWN/'old-binary.py',OWN/'ContainerProbe/main.go']
 paths.extend(v for v in (ROOT/'services').rglob('*') if v.is_file() and v.suffix in ['.go','.sql','.json'] and 'verification' not in v.relative_to(ROOT/'services').parts)
 paths.extend([ROOT/'services/release/README-v3.md',ROOT/'services/release/POSTGRES.md'])
 return {str(v.relative_to(ROOT)):digest(v) for v in sorted(set(paths))}
base=inputs();assert base['services/release/migrations/001_release.sql']=='c352755698244eff1a5d65ac32d0255478ea270be1fc143a94bdbba876b47605'
for name,checksum in base.items():
 target=source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes());target.chmod(0o444)
manifest=''.join(d+'  '+n+'\n' for n,d in base.items());(out/'source-manifest.sha256').write_text(manifest)
record={'status':'running','scope':'Implementer explicit development-service-v3 qualification; independent review remains separate','repositoryHeadAtRun':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'protocolRevision':'c5bf3fee0c7823d976861d7c452ef3245980df30','source':base,'sourceManifestSHA256':sha(manifest.encode()),'frozenSourceExport':str(source),'commands':[],'limitations':['Local macOS arm64 Go/PostgreSQL; no hosted Linux deployment or device execution','Disposable private Unix-socket cluster; no installed/production database, credential or trust mutation','Static development bearer bootstrap; no customer identity, outbox dispatch, backup/restore, multi-zone, CDN, client activation or GA claim','Synthetic signed service payloads are not executable authorization; native clients independently verify all bytes/current authority']}
def save(): (out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
def run(name,cmd,cwd,timeout=240):
 began=time.monotonic();r=subprocess.run(list(map(str,cmd)),cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(out/(name+'.log')).write_bytes(r.stdout);item={'name':name,'command':list(map(str,cmd)),'cwd':str(cwd),'exitCode':r.returncode,'elapsedSeconds':time.monotonic()-began,'logSHA256':sha(r.stdout)};record['commands'].append(item);save();print(name+': '+str(r.returncode),flush=True);return r,item
save()
for name,cmd in [('go-version',['go','version']),('go-environment',['go','env','GOROOT','GOVERSION','GOOS','GOARCH','GOTOOLCHAIN']),('host-version',['uname','-a']),('postgres-version',['postgres','--version']),('python-version',['python3','--version'])]:run(name,cmd,source/'services')
r,item=run('go-race',['go','test','-race','-count=1','-json','./...'],source/'services')
events=[]
for line in r.stdout.splitlines():
 try:events.append(json.loads(line))
 except ValueError:pass
passed={e.get('Test') for e in events if e.get('Action')=='pass'};required={'TestHTTPV3CoexistenceConcurrentSequenceAndMonotonicReopen','TestHTTPV3ScopeRolesCurrentAuthorityAndHostBinding','TestV3HostConfigurationUsesClosedProtocolCeilings','TestHTTPV3ClosedEnvelopeMalformedAndWholeDocumentLimits','TestHTTPV3LocalUpgradeFaultsReopenAndRetry','TestV3StorageVariantsAreClosedAtomicAndRejectOlderContainers','TestHTTPV3ExactPayloadCeilingAndCorruptReopen','TestHTTPV2CoexistsWithLegacyAndPreservesRuntimeChannels'}
item['requiredTests']=sorted(required);item['requiredTestsPassed']=required<=passed;item['skips']=[e.get('Test') for e in events if e.get('Action')=='skip' and e.get('Test')];item['topLevelPassCounts']={pkg:sum(1 for e in events if e.get('Action')=='pass' and e.get('Package')==pkg and e.get('Test') and '/' not in e['Test']) for pkg in sorted({e.get('Package') for e in events if e.get('Package')})};save()
run('go-vet',['go','vet','./...'],source/'services')
run('postgres',['python3','-B',source/'services/verification/postgres.py','--output',out/'postgres'],source,timeout=300)
run('old-binary',['python3','-B',source/'verification/release-v3-service/old-binary.py','--output',out/'old-binary','--services',source/'services','--repository',ROOT],source)
record['subreceipts']={}
for name in ['postgres','old-binary']:
 path=out/name/'receipt.json'
 if path.exists():
  value=json.loads(path.read_text());record['subreceipts'][name]={'sha256':digest(path),'status':value['status']}
  if name=='postgres':
   text=(out/'postgres/real-postgres-tests.stdout').read_text();record['subreceipts'][name]['v3TestsPresent']=all(('--- PASS: '+test) in text for test in ['TestPostgresV3CoexistenceRLSReplayAndRuntimeIsolation','TestPostgresV3InterruptedPublicationImmediateRestart']);record['subreceipts'][name]['noSkippedCases']='--- SKIP:' not in text;record['subreceipts'][name]['privateClusterRemoved']=value.get('privateClusterRemoved')
record['sourceUnchanged']=inputs()==base;record['exportUnchanged']=all(digest(source/name)==checksum for name,checksum in base.items());record['protocolUnchangedFromReviewedRevision']=all(subprocess.check_output(['git','show',record['protocolRevision']+':'+name],cwd=ROOT)==(ROOT/name).read_bytes() for name in base if name.startswith('services/protocol/') or name=='contracts/release-v2.json')
record['status']='scoped_checks_passed' if all(c['exitCode']==0 for c in record['commands']) and item['requiredTestsPassed'] and not item['skips'] and len(record['subreceipts'])==2 and all(v['status']=='passed' and v.get('v3TestsPresent',True) and v.get('noSkippedCases',True) and v.get('privateClusterRemoved',True) for v in record['subreceipts'].values()) and record['sourceUnchanged'] and record['exportUnchanged'] and record['protocolUnchangedFromReviewedRevision'] else 'failed_check_preserved';save();raise SystemExit(0 if record['status']=='scoped_checks_passed' else 1)
