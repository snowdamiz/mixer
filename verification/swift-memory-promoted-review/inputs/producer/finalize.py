#!/usr/bin/env python3
"""Freeze observed evidence, then retire only this lane's owned scratch."""
from pathlib import Path
import collections,datetime,difflib,gzip,hashlib,json,shutil,subprocess,tarfile
from run import HERE,SCRATCH,b
ROOT=HERE.parents[1]
old_receipt=json.loads((HERE/'inputs/behavior-receipt.json').read_text())
review=json.loads((HERE/'inputs/review-receipt.json').read_text())
assert review['verdict']=='request-changes' and review['blockingFindings']==['MR01']
archives={}
for label,path in [('baseline',SCRATCH/'baseline/vm'),('behavior',SCRATCH/'behavior/vm'),('candidate',SCRATCH/'candidate/vm'),('metadata-baseline',SCRATCH/'metadata-baseline-binary'),('metadata-candidate',SCRATCH/'metadata-candidate-binary')]:
 m=b.manifest(path);(HERE/(label+'-source-manifest.json')).write_bytes(b.enc(m))
 with tarfile.open(HERE/(label+'-source.tar.gz'),'w:gz') as t:
  for n in m:t.add(path/n,arcname='vm/'+n,recursive=False)
 with tarfile.open(HERE/(label+'-source.tar.gz')) as t:assert {x.name.removeprefix('vm/'):hashlib.sha256(t.extractfile(x).read()).hexdigest() for x in t.getmembers()}==m
 archives[label]=dict(files=len(m),closure=b.digest(m),archiveSHA256=b.sha(HERE/(label+'-source.tar.gz')))
assert archives['baseline']['closure']==old_receipt['baselineSourceClosure']
assert archives['behavior']['closure']==old_receipt['candidateSourceClosure']
source=archives['candidate']['closure']
schema=json.loads((HERE/'inventory-schema.json').read_text());old_schema=json.loads((HERE/'inputs/behavior-inventory-schema.json').read_text());old_fields={r['field']:r for r in old_schema};new_fields={r['field']:r for r in schema}
assert len(new_fields)==len(schema)==4800 and all(new_fields[n]==r for n,r in old_fields.items())
added=[r for r in schema if r['field'] not in old_fields];assert len(added)==8 and all(r['config']=='unit' and r['mirFunction']=='memory_pinned_step::promoted[0]' for r in added)
old_manifest=b.manifest(SCRATCH/'behavior/vm');new_manifest=b.manifest(SCRATCH/'candidate/vm');changed=[n for n in set(old_manifest)|set(new_manifest) if old_manifest.get(n)!=new_manifest.get(n)]
path='src/experimental_swift_reactor/memory_operations.rs';assert changed==[path]
before=(SCRATCH/'behavior/vm'/path).read_text();after=(SCRATCH/'candidate/vm'/path).read_text();assert before.split('// ACCOUNTING_START')[0]==after.split('// ACCOUNTING_START')[0]
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/vm/'+path,tofile='b/vm/'+path));assert (HERE/'correction.patch').read_text()==patch
delta=dict(behaviorSourceClosure=archives['behavior']['closure'],candidateSourceClosure=source,changedFiles=changed,unchangedFiles=len(new_manifest)-1,executablePrefixUnchanged=True,dependencyManifestsUnchanged=all(old_manifest[n]==new_manifest[n] for n in ['Cargo.toml','Cargo.lock']),oldSchemaRowsRetainedExactly=len(old_schema),addedFields=added,productionCanonicalFields=sum(r['config']=='production' for r in schema),unitCanonicalFields=sum(r['config']=='unit' for r in schema),schemaHistoricalProvenanceRetained=True,freshCompilerLocations='canonical-audit.json')
(HERE/'source-delta.json').write_bytes(b.enc(delta))
layouts=json.loads((HERE/'layouts.json').read_text());previous=json.loads((HERE/'inputs/behavior-layouts.json').read_text());layout_delta=[]
for layout in [x for x in layouts if x['label']=='candidate']:
 old=next(x for x in previous if x['label']=='candidate' and all(x[k]==layout[k] for k in ['features','profile','unit']))
 assert layout['owners']==old['owners'] and layout['types']==old['types']
 for n in old['fields']:assert layout['fields'][n]['bytes']==old['fields'][n]['bytes'] and layout['fields'][n]['alignment']==old['fields'][n]['alignment']
 total_delta={n:layout['totals'][n]-old['totals'][n] for n in old['totals']}
 assert {n:v for n,v in total_delta.items() if v}==({'memory_active':64,'frame':64} if layout['unit'] else {})
 observed=[layout['fields'][r['field']] for r in added] if layout['unit'] else []
 assert sum(f['bytes'] for f in observed)==(64 if layout['unit'] else 0)
 layout_delta.append(dict(features=layout['features'],profile=layout['profile'],unit=layout['unit'],totalsDelta=total_delta,additionalMeasuredFields=observed,additionalMeasuredFieldBytes=sum(f['bytes'] for f in observed),containingOwnersUnchanged=True,oldFieldSizesAndAlignmentsUnchanged=True))
(HERE/'layout-delta.json').write_bytes(b.enc(layout_delta))
matrix=json.loads((HERE/'matrix-results.json').read_text());assert len(matrix)==64
for r in matrix:
 assert r['sourceClosure']==source;r['observedHarnessFixtureCount']=r.pop('observedFixtureCount');r['auxiliaryRealOwnerCount']=1 if r['id']=='mm07_pinned_decoded_caller' else 0;r['boundedRealOwnerCount']=r['observedHarnessFixtureCount']+r['auxiliaryRealOwnerCount'];assert r['boundedRealOwnerCount']<=64
(HERE/'matrix-results.json').write_bytes(b.enc(matrix))
commands=[];binaries=[];qualified=[]
for directory in sorted((HERE/'commands').iterdir()):
 r=json.loads((directory/'receipt.json').read_text());commands.append(dict(name=directory.name,exitCode=r['exitCode'],sourceClosure=r['sourceTreeSHA256']))
 if directory.name!='collector-regression':
  assert r['exitCode']==0 and r['sourceUnchanged'];qualified.append(directory.name)
 for v in r.get('executables',[]):binaries.append(dict(command=directory.name,sourceClosure=r['sourceTreeSHA256'],**v))
 for stream in ['stdout','stderr']:
  raw=directory/stream;assert b.sha(raw)==r[stream+'SHA256'];(directory/(stream+'.gz')).write_bytes(gzip.compress(raw.read_bytes(),mtime=0));raw.unlink()
(HERE/'command-index.json').write_bytes(b.enc(commands));(HERE/'executable-manifest.json').write_bytes(b.enc(binaries))
(HERE/'failed-attempts.json').write_bytes(b.enc([dict(command='collector-regression',classification='verification-metadata-retention-only',exitCode=1,candidateSourceClosure=source,candidateSourceUnchanged=True,script='historical/collector-regression-v1.py',generator='historical/inventory-v1.py',reconstructedExactSchema='historical/collector-v1-inventory-schema.json',reason='The first generated schema retained all fields but refreshed historical compiler qualifications/line numbers. Exact-row retention assertion failed; generator now preserves every original row exactly and records fresh MIR positions separately. Runtime source was already the same eight-field correction.')] ))
identity=json.loads((HERE/'frozen-identity.json').read_text());previous_identity=json.loads((HERE/'inputs/behavior-frozen-identity.json').read_text());assert identity['methods']==previous_identity['methods'] and identity['containingOwners']==previous_identity['containingOwners']
reuse=dict(status='reused-immutable-observations-with-exact-source-equivalence',behaviorReceiptSHA256=b.sha(HERE/'inputs/behavior-receipt.json'),behaviorSourceClosure=archives['behavior']['closure'],correctionSourceClosure=source,onlySourceDelta=path,deltaOnlyUninstantiatedCfgTestAccountingFields=True,executablePrefixUnchanged=True,compiledFrozenMethodsIdentical=identity['count'],containingOwnersUnchanged=len(identity['containingOwners']),dependencyManifestsUnchanged=True,observationPairs=56,fixturesPerProfile=28,integrationTestsPerRun=16,integrationRuns=4,reusedCommandNames=sorted(p.name for p in (HERE/'reused-frozen/commands').iterdir()),reexecutedInCorrection=False,reason='Exact entire-source comparison permits only eight cfg(test) logical accounting fields; all executable code and all 39 compiler-expanded Frozen methods plus owner declarations/dependencies are identical. Concrete prior baseline/candidate observations and their exact instrumented sources remain copied and bound.')
(HERE/'frozen-runtime-reuse.json').write_bytes(b.enc(reuse))
versions={n:gzip.decompress((HERE/'commands'/('tool-'+n)/'stdout.gz').read_bytes()).decode().strip() for n in ['rustc','cargo','rustfmt','python','host','git']}
prod=next(x for x in layouts if x['label']=='candidate' and x['features']=='all' and x['profile']=='debug' and not x['unit'])['totals'];unit=next(x for x in layouts if x['label']=='candidate' and x['features']=='all' and x['profile']=='debug' and x['unit'])['totals']
doc=f'''# Swift memory promoted accounting correction

The bounded private correction adds the standalone unit caller promotion omitted
by MR01. Its 123-file source closure is `{source}`. The reviewed behavior source
remains `{archives['behavior']['closure']}` and the accepted live control baseline
remains `{archives['baseline']['closure']}`. Live VM code was not edited.

The promoted-body collector applies the same `selected(name)` rule as function
bodies. Actual compiler MIR contains `memory_pinned_step::promoted[0]` with a
`&LocalKey<Cell<bool>>` return and `LocalKey<Cell<bool>>` backing place. Each now
has distinct source, argument, returned and caller positions. All 4,792 original
schema rows and source fields remain; eight additional unit fields bring the
inventory to 4,800 (2,104 production canonical, 2,164 additional unit canonical,
480 authored active and 52 authored permanent). Historical schema metadata is
retained exactly; the fresh canonical audit records current compiler locations.

Only eight `#[cfg(test)]` accounting fields differ from the behavior source.
Every executable source byte, dependency manifest, owner declaration, limit,
ticket and diagnostic is unchanged. A collector regression includes the actual
standalone promotion, excludes actual test-module promotions and preserves all
original rows. Four fresh Swift-only/all-feature production/unit compiler MIR
configurations reproduce every positive role, including captures, aliases,
literals, width and all selected promotions.

Sixteen paired actual compiler layout runs measure every positive field and its
containing struct, with disjoint offsets. The eight new fields each measure eight
bytes and increase unit active/frame bounds by 64 bytes. Original owner sizes,
alignments and offsets remain unchanged across features/profiles.

| aarch64 host named-object bound | Production | Unit |
| --- | ---: | ---: |
| Memory active addition | {prod['memory_active']:,} | {unit['memory_active']:,} |
| Memory permanent addition | {prod['memory_permanent']:,} | {unit['memory_permanent']:,} |
| Execution header | {prod['header']:,} | {unit['header']:,} |
| Complete frame operation envelope | {prod['frame']:,} | {unit['frame']:,} |
| Construction envelope | {prod['construction']:,} | {unit['construction']:,} |

All sixteen frozen MM01–MM16 names execute once in each Swift-only/all-feature
Debug/Release configuration: 64 successful memory selections. The prior 34
frame/control and 12 value tests pass in all four configurations. Eight
default/span/Swift/all Debug/Release library checks pass. Runtime commands use
the exact corrected source; layout programs use separately archived instrumented
copies. No runtime algorithm, control flow, limit, ticket or test expectation
changes are part of this correction.

All 39 compiler-expanded Frozen methods and fourteen owner declarations match
both the reviewed behavior source and original accepted baseline. Frozen retains
its 2,912-byte reservation, the authority remains 86 tickets and State/Combined
limits remain 128/256 MiB. Exact source equivalence supports explicit reuse of
the immutable 56 actual Frozen baseline/candidate observation pairs and four
16-test integration runs. Their commands, outputs, source archives/manifests and
the source-equivalence proof are copied and bound; those executions were not
repeated by this correction. Swift-only MM14 still records Frozen feature absence.

The packet retains exact archives, commands/tools/outputs/executable hashes,
current MIR, measured layouts, the first failed metadata-retention check and its
exact script/input reconstruction, and cleanup. The standalone read-only checker
is `python3 -B verification/swift-memory-promoted-correction/verify.py` (optional
`--live-baseline`). Only this lane's disposable scratch was removed; no native,
simulator/emulator, physical-phone or UI execution ran.

Fresh independent correction review and root acceptance remain required. G08
still has the preserved absent-cursor Cleanup diagnostic. Logical named-object
accounting is not compiler stack, allocator overhead or RSS. Swift bulk memory
and growth, full dispatcher/Ready/public invocation, native joins, immutable
published separate-repository FieldLog, physical phones, signing, store,
customer, operational and GA gates remain open. This is a bounded host slice.
'''
(ROOT/'docs/swift-memory-promoted-correction.md').write_text(doc)
(HERE/'README.md').write_text('''# Frozen bounded promoted accounting correction

Run `python3 -B verification/swift-memory-promoted-correction/verify.py`.
The checker reads only archived evidence. `--live-baseline` adds the live control
closure check. Candidate/metadata source archives are authoritative; session
scratch paths are historical and are removed. Reproduce only in a fresh unsealed
copy with a fresh uniquely owned scratch; never modify a frozen packet.

The final source has eight new unit accounting fields only. Historical schema
rows retain their original provenance; canonical-audit.json records fresh actual
compiler locations and exact role matches in four configurations. Runtime and
layout commands have distinct archived source identities. Frozen runtime results
are explicitly reused with exact source-equivalence evidence, not rerun here.
Fresh independent correction review and root acceptance remain pending.
''')
files=[p for p in SCRATCH.rglob('*') if p.is_file()];cleanup=dict(scratch=str(SCRATCH),files=len(files),logicalFileBytes=sum(p.stat().st_size for p in files),sourceArchivesVerifiedBeforeRemoval=list(archives),deviceInstancesCreated=0,simulatorOrEmulatorStarted=False,processesTerminated=False,otherProjectDataTouched=False)
probe=subprocess.run(['/usr/sbin/lsof','-nP','+D',str(SCRATCH)],capture_output=True)
for stream in ['stdout','stderr']:(HERE/('cleanup-lsof.'+stream+'.gz')).write_bytes(gzip.compress(getattr(probe,stream),mtime=0))
cleanup.update(lsofExitCode=probe.returncode,lsofObservedNoOpenFiles=probe.returncode==1 and not probe.stdout);assert cleanup['lsofObservedNoOpenFiles'] and SCRATCH.name.startswith('mixer-swift-memory-promoted-correction-');shutil.rmtree(SCRATCH);cleanup.update(ownedScratchRemoved=not SCRATCH.exists(),completedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat());(HERE/'cleanup.json').write_bytes(b.enc(cleanup))
receipt=dict(schema=1,status='candidate-frozen-for-independent-correction-review',scope='MR01 bounded private host promoted accounting correction only',candidateSourceClosure=source,behaviorSourceClosure=archives['behavior']['closure'],baselineSourceClosure=archives['baseline']['closure'],sourceArchives=archives,positiveFields=len(schema),originalRowsRetainedExactly=len(old_schema),additionalUnitFields=len(added),productionCanonicalFields=delta['productionCanonicalFields'],additionalUnitCanonicalFields=delta['unitCanonicalFields'],measuredAdditionalUnitActiveBytes=unit['memory_active']-old_receipt['unitMemoryActiveBytes'],productionMemoryActiveBytes=prod['memory_active'],unitMemoryActiveBytes=unit['memory_active'],memoryPermanentBytes=prod['memory_permanent'],productionHeaderBytes=prod['header'],unitHeaderBytes=unit['header'],productionFrameBytes=prod['frame'],unitFrameBytes=unit['frame'],stateLimitBytes=prod['state_limit'],combinedLimitBytes=prod['combined_limit'],maximumReservationTickets=86,frozenReservationBytes=2912,frozenIdenticalExpandedMethods=39,memoryTestsExecuted=64,priorFrameControlTestsPerConfiguration=34,priorValueTestsPerConfiguration=12,priorConfigurations=4,actualPairedLayouts=16,actualMIRConfigurations=4,collectorRegressionTests=3,reusedFrozenObservationPairs=56,reusedFrozenIntegrationRuns=4,qualifyingCommands=qualified,toolVersions=versions,cleanup=cleanup,logicalNamedObjectAccountingOnly=True,independentReviewAccepted=False,rootAcceptance=False,liveVMEdited=False,fullDispatcher=False,readyOrPublicInvocation=False,nativeRuntime=False,physicalRuntime=False,UI=False,publishedFieldLogQualified=False,gaAcceptance=False,committed=False,pushed=False,G08='pending-preserved-absent-cursor-Cleanup-diagnostic',limitations=['Host logical named-object bounds only; no compiler stack, allocator overhead or RSS claim.','Frozen runtime observations are explicit immutable reuse, not new executions.','Independent correction review and root acceptance remain pending.','Full dispatcher/public invocation, G08 diagnostics, native/mobile/physical/published FieldLog/signing/store/customer/operational/GA gates remain open.'],documentationSHA256=b.sha(ROOT/'docs/swift-memory-promoted-correction.md'),observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat())
for p in HERE.rglob('__pycache__'):shutil.rmtree(p)
receipt['bindings']={str(p.relative_to(HERE)):b.sha(p) for p in sorted(HERE.rglob('*')) if p.is_file() and p.name not in ['offline-verify.log'] and p not in [HERE/'receipt.json',HERE/'seal.json']};receipt['boundEvidenceFiles']=len(receipt['bindings']);(HERE/'receipt.json').write_bytes(b.enc(receipt));(HERE/'seal.json').write_bytes(b.enc(dict(receiptSHA256=b.sha(HERE/'receipt.json'),candidateSourceClosure=source,independentReviewAccepted=False,rootAcceptance=False)))
print('frozen',source,'bindings',receipt['boundEvidenceFiles'],'receipt',b.sha(HERE/'receipt.json'),flush=True)
