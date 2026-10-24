#!/usr/bin/env python3
"""Freeze fresh observations and remove only this review's owned scratch."""
from pathlib import Path
import gzip, hashlib, json, os, re, shutil
from review import HERE, ROOT, enc, digest, sha, manifest, now, read, run

def parse_layout(name):
 text=gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode();result={k:{} for k in ['types','fields','classes','totals']}
 for line in text.splitlines():
  if 'PR_' not in line:continue
  kind,key,*values=line[line.index('PR_'):].split();values=list(map(int,values));target={'PR_TYPE':'types','PR_FIELD':'fields','PR_CLASS':'classes','PR_TOTAL':'totals'}[kind]
  assert key not in result[target]
  result[target][key]=dict(offset=values[0],bytes=values[1],alignment=values[2]) if target=='fields' else dict(bytes=values[0],alignment=values[1]) if target in ['types','classes'] else values[0]
 assert '1 passed; 0 failed; 0 ignored' in text
 return result

def main():
 behavior=parse_layout('fresh-layout-behavior');candidate=parse_layout('fresh-layout-candidate')
 assert behavior['types']==candidate['types']=={'_0':dict(bytes=8,alignment=8),'_1':dict(bytes=8,alignment=8)}
 assert behavior['totals']==dict(active=1142696,permanent=121856,frame=5092824)
 assert candidate['totals']==dict(active=1142760,permanent=121856,frame=5092888)
 added=read('source-review.json')['exactAddedRows'];assert set(candidate['fields'])=={r['field'] for r in added}
 end=0
 for f in sorted(candidate['fields'].values(),key=lambda v:v['offset']):assert f['bytes']==f['alignment']==8 and f['offset']>=end and f['offset']%8==0;end=f['offset']+8
 assert sum(f['bytes'] for f in candidate['fields'].values())==64 and end<=candidate['classes']['active']['bytes']
 results=[]
 for feature in ['swift','all']:
  for profile in ['debug','release']:
   for test in ['af05','af22','mm16']:
    name='affected-'+feature+'-'+profile+'-'+test;c=read('commands/'+name+'/receipt.json');out=gzip.decompress((HERE/'commands'/name/'stdout.gz').read_bytes()).decode();assert c['exitCode']==0 and '1 passed; 0 failed; 0 ignored' in out and c['executables']
    assert c['sourceClosure']=='a01da340253ad086e69c060a041d8d15b3f9bb7a63f8c11465af704ce01ef65b'
    if test=='af22':assert 'frame=5092888' in out and 'frame_admitted=false' in out
    results.append(dict(command=name,feature=feature,profile=profile,test=test,passed=True,exactSource=True))
 fresh=dict(typedPairedUnitLayouts={'behavior':behavior,'candidate':candidate},typesMatchActualFields=True,additionalNamedUnitBytes=64,activeDelta=64,frameDelta=64,permanentDelta=0,affectedBoundSelections=results,freshCanonicalMIRConfigurations=1,compilerStackOrRSS=False)
 (HERE/'fresh-results.json').write_bytes(enc(fresh))
 failures=dict(qualificationCompilerOrRuntimeFailures=[],reviewAuditDraftFailures=[dict(command='reuse-audit-draft-v1',script='failed-attempts/reuse_audit_v1.py',reason='The independent draft included the pub visibility prefix in six method hashes; baseline and candidate method text agreed, but the producer hash convention begins at fn. The corrected parser begins at fn and reproduces all 39 frozen hashes. No candidate implementation changed.')],inspectionOnlyFailures=[dict(command='cat verification/swift-memory-promoted-correction/frozen-source-equivalence.json',exitCode=1,stderr='No such file or directory',resolution='The packet uses frozen-runtime-reuse.json; inspected and bound the actual file. No source or command qualification changed.')],producerFailuresRetained='inputs/producer/failed-attempts.json')
 (HERE/'failed-attempts.json').write_bytes(enc(failures))
 notes=read('integration-notes.json');assert len(notes['trailingWhitespace'])==2
 findings=dict(verdict='accepted-scoped-correction',blockingFindings=[],resolvedFindings=[dict(id='MR01',resolution='Standalone caller promotion is selected by the function/promoted shared selector; actual return and backing places each have four distinct fields; fresh compiler measurements confirm 64 additional unit bytes.')],integrationNotes=[dict(id='IN01',severity='nonblocking-for-frozen-correction',detail='Inherited whitespace-only lines at src/experimental/execution/mod.rs:1139-1140 require root-owned normalization before integration.',evidence='integration-notes.json')],rootAcceptance=False,gaAcceptance=False)
 (HERE/'findings.json').write_bytes(enc(findings))
 scratch=Path(read('session.json')['scratch']);assert scratch.is_dir() and scratch.name.startswith('mixer-promoted-independent-review-')
 validated=[]
 for label in ['behavior','candidate','probe-behavior','probe-candidate']:
  expected=read(('inputs/producer/' if label in ['behavior','candidate'] else '')+label+'-source-manifest.json')
  assert manifest(scratch/label/'vm')==expected;validated.append(dict(label=label,closure=digest(expected)))
 paths=[p for p in scratch.rglob('*') if p.is_file()];files=len(paths);logicalbytes=sum(p.stat().st_size for p in paths)
 p=run('cleanup-lsof',['lsof','-nP','+D',str(scratch)])
 assert p.returncode==1 and not p.stdout and not p.stderr
 shutil.rmtree(scratch);assert not scratch.exists()
 cleanup=dict(completedUTC=now(),scratch=str(scratch),sourceArchivesVerifiedBeforeRemoval=validated,filesRemoved=files,logicalFileBytesRemoved=logicalbytes,lsofExitCode=p.returncode,lsofObservedNoOpenFiles=True,ownedScratchRemoved=True,deviceInstancesCreated=0,simulatorOrEmulatorStarted=False,otherProjectDataTouched=False,processesTerminated=False)
 (HERE/'cleanup.json').write_bytes(enc(cleanup))
 commands=[]
 for f in sorted((HERE/'commands').glob('*/receipt.json')):
  c=json.loads(f.read_text());commands.append(dict(name=f.parent.name,exitCode=c['exitCode'],sourceClosure=c['sourceClosure']))
 (HERE/'command-index.json').write_bytes(enc(commands))
 print('fresh typed layouts and 12 exact bound selections qualified; owned scratch removed',flush=True)

if __name__=='__main__':main()
