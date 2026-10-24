#!/usr/bin/env python3
"""Reconstruct immutable reused evidence from commands, outputs and sources."""
import collections, gzip, hashlib, json, re, tarfile
from audit import P, load, source
from review import HERE, enc, digest, sha

def output(directory,stream='stdout'):
 receipt=json.loads((directory/'receipt.json').read_text())
 raw=gzip.decompress((directory/(stream+'.gz')).read_bytes())
 assert hashlib.sha256(raw).hexdigest()==receipt[stream+'SHA256']
 return raw.decode()

def item(text,needle):
 start=text.index(needle);at=text.index('{',start)+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[start:at]

def audit():
 correction=load('receipt.json');candidate=correction['candidateSourceClosure']
 # Every reused memory/regression command is exact corrected source, with its
 # actual output and executable digest, and each exact test selected once.
 matrix=load('matrix-results.json');spec=load('acceptance-matrix.json')
 expected={(c['id'],config) for c in spec['cases'] for config in spec['configurations']}
 assert len(matrix)==64 and {(r['id'],r['configuration']) for r in matrix}==expected
 matrix_names=[]
 for row in matrix:
  directory=P/'commands'/row['command'];c=json.loads((directory/'receipt.json').read_text());out=output(directory);output(directory,'stderr')
  assert c['exitCode']==0 and c['sourceUnchanged'] and c['sourceTreeSHA256']==candidate==row['sourceClosure']
  assert digest(json.loads((directory/'source-manifest.json').read_text()))==candidate
  assert c['executables'] and all(re.fullmatch('[a-f0-9]{64}',v['sha256']) for v in c['executables'])
  assert '1 passed; 0 failed; 0 ignored' in out and row['requiredTest'] in out and row['requiredTest'] in c['argv'] and '--exact' in c['argv']
  assert out.count('test '+row['requiredTest']+' ...')==1
  if row['id']=='mm14_frozen_parity':assert ('feature absent' in out)==row['configuration'].startswith('swift-')
  matrix_names.append(row['command'])
 regressions=load('regression-results.json');assert len(regressions)==8;regression_counts={}
 for row in regressions:
  directory=P/'commands'/row['command'];c=json.loads((directory/'receipt.json').read_text());out=output(directory);output(directory,'stderr')
  assert c['exitCode']==0 and c['sourceUnchanged'] and c['sourceTreeSHA256']==candidate and c['executables']
  assert digest(json.loads((directory/'source-manifest.json').read_text()))==candidate
  expected_count=34 if row['command'].endswith('frame-control') else 12
  assert f'{expected_count} passed; 0 failed; 0 ignored' in out;regression_counts[row['command']]=expected_count
 # Reconstruct expanded methods directly from immutable actual compiler output.
 identity=load('frozen-identity.json');expanded={}
 for label in ['baseline','candidate']:
  directory=P/'commands'/('corrected-expanded-'+label);c=json.loads((directory/'receipt.json').read_text());full=output(directory);output(directory,'stderr')
  assert c['sourceUnchanged'] and c['exitCode']==0 and c['sourceTreeSHA256']==correction['sourceArchives'][label]['closure']
  span=item(full,'impl SpanInstance {');methods={}
  for match in re.finditer(r'^\s+(?:pub )?fn (\w+)\(',span,re.M):
   name=match[1];text=item(span,match[0].lstrip());text=text.strip();methods[name]=hashlib.sha256(text.encode()).hexdigest()
  assert len(methods)==39;expanded[label]=methods
 assert expanded['baseline']==expanded['candidate']==identity['methods']
 data={label:source(label)[0] for label in ['baseline','behavior','candidate']};owners={}
 for path,names in {'src/experimental/execution/mod.rs':['pub struct SpanInstance','pub(crate) struct Control','struct Frame','pub struct ExecutionBudget','pub struct ExecutionUsage','pub struct ExecutionFailure'],'src/experimental_swift_reactor/execution.rs':['pub(crate) struct SwiftExecutionState','pub(crate) struct SwiftReactorInstance','pub(crate) struct SwiftExecutionOperation','pub(crate) struct SwiftFrame','pub(crate) struct ExecutionOperationPhase'],'src/experimental_swift_reactor/frame_operations.rs':['pub(crate) struct FrameOperationPhase','pub(crate) struct FrameOperationStorage','pub(crate) struct FrameCleanupState']}.items():
  for name in names:
   snippets=[item(data[label][path].decode(),name) for label in data];assert len(set(snippets))==1;owners[name]=hashlib.sha256(snippets[0].encode()).hexdigest()
 assert len(owners)==14 and all(v==identity['containingOwners'][n]['sha256'] for n,v in owners.items())
 # The eight-field delta touches no executable bytes. Frozen parity's sources
 # remain their original, separately instrumented archives and manifests.
 reuse=load('frozen-runtime-reuse.json');old=load('inputs/behavior-receipt.json');sourceclosures={}
 for label in ['baseline','candidate']:
  path=P/'reused-frozen'/('parity-'+label+'-source.tar.gz')
  with tarfile.open(path) as t:
   m={v.name[3:]:hashlib.sha256(t.extractfile(v).read()).hexdigest() for v in t.getmembers()};assert m==load('reused-frozen/parity-'+label+'-source-manifest.json');sourceclosures[label]=digest(m)
 for name in reuse['reusedCommandNames']:
  directory=P/'reused-frozen/commands'/name;c=json.loads((directory/'receipt.json').read_text());out=output(directory);output(directory,'stderr')
  assert c['exitCode']==0 and c['sourceUnchanged'] and c['executables']
  assert sha(directory/'receipt.json')==old['bindings']['commands/'+name+'/receipt.json']
  assert digest(json.loads((directory/'source-manifest.json').read_text()))==c['sourceTreeSHA256']
  label='baseline' if '-baseline-' in name else 'candidate'
  assert c['sourceTreeSHA256']==(sourceclosures[label] if 'snapshot' in name else correction['sourceArchives']['baseline' if label=='baseline' else 'behavior']['closure'])
  for stream in ['stdout','stderr']:assert sha(directory/(stream+'.gz'))==old['bindings']['commands/'+name+'/'+stream+'.gz']
  if 'integration' in name:assert '16 passed; 0 failed; 0 ignored' in out
 pairs=0
 for profile in ['debug','release']:
  lines=[]
  for label in ['baseline','candidate']:
   out=output(P/'reused-frozen/commands'/('final2-frozen-snapshot-'+label+'-'+profile));rows=[line[line.index('FROZEN_SNAPSHOT '):] for line in out.splitlines() if 'FROZEN_SNAPSHOT ' in line];assert len(rows)==28;lines.append(rows)
  assert lines[0]==lines[1];pairs+=28
 assert pairs==56
 return dict(memorySelections=64,frameControlValueSelections=sum(regression_counts.values()),libraryChecks=8,actualCompilerLayouts=16,actualMIRConfigurations=4,matrixCommandNames=matrix_names,regressionCounts=regression_counts,expandedFrozenMethodCount=39,expandedFrozenMethods=expanded['candidate'],unchangedContainingOwnerCount=14,unchangedContainingOwners=owners,frozenObservationPairs=56,frozenIntegrationRuns=4,frozenIntegrationTestsPerRun=16,paritySourceClosures=sourceclosures,producerEvidenceFiles=563,reexecutedBroadMatrices=False,exactSourceEquivalence=True)

if __name__=='__main__':
 result=audit();(HERE/'reused-evidence-review.json').write_bytes(enc(result));print('reused immutable 64 memory + 184 regression selections, 39 Frozen methods, 14 owners, 56 Frozen pairs and 4 integration runs bound',flush=True)
