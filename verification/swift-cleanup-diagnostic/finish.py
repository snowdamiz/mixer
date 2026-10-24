#!/usr/bin/env python3
"""Finalize only completed, exact candidate evidence. Does not integrate source."""
import gzip,json,re,sys,tarfile,os,shutil,subprocess
from pathlib import Path
import collect as c

def finalize():
 h=c.HERE;source=c.digest(c.manifest(c.source('candidate')));assert source==c.digest(json.loads((h/'candidate-source-manifest.json').read_text()))
 assert source==json.loads((h/'accounting-qualification.json').read_text())['sourceSHA256']
 runtime=[json.loads((h/('final-runtime-'+f+'-'+p+'.json')).read_text())for f in ['swift','all']for p in ['debug','release']]
 assert all(x['sourceTreeSHA256']==source and len(x['selectedTests'])==17 for x in runtime)
 assert [x['passed']for x in runtime]==[252,252,282,282]
 selected=runtime[0]['selectedTests'];all_tests=json.loads((h/'artifacts/final-runtime-all-release/test-list.json').read_text())
 definitions={
 'CDR01':['cdr01_'], 'CDR02':['cdr02_'], 'CDR03':['cdr03_','sc09_defensive_live_faults'],
 'CDR04':['cdr04_'],'CDR05':['cdr05_'],'CDR06':['cdr06_'],'CDR07':['cdr07_'],
 'CDR08':['cdr08_'],'CDR09':['cdr09_'],'CDR10':['cdr10_','mg18_sticky_uncommitted_debt_refuses_completion','live_cleanup_underflow_retains_counts_and_remaining_cleanup_still_drains'],
 'CDR11':['cdr11_','af17_real_prior_wasi_effect_and_sticky_first_failure','af18_dropped_phase_cleanup_resume_has_no_admission_work_or_value_access','af19_exact_fixed_storage_outer_restore_rejection_and_retry','af20_original_provenance_layout_and_consuming_barriers_preserve_owners'],
 'CDR12':['mm04_opcode_type_floor_closed','mm06_cancel_prefix','mm07_pinned_decoded_caller','mg10_pinned_failures_before_effects'],
 'CDR13':['cdr13_','mm13_no_alloc_warm','bm14_no_alloc_and_deferred'],
 'CDR14':['cdr14_'],'CDR15':[],'CDR16':[],'CDR17':['cdr17_']}
 groups={}
 for group,patterns in definitions.items():
  tests=[n for n in all_tests if any(n.split('::')[-1].startswith(p)for p in patterns)]
  assert tests or group in ['CDR15','CDR16'],(group,patterns)
  groups[group]={'status':'producer-observed-independent-review-pending','exactTests':tests,'contexts':['swift-debug','swift-release','all-debug','all-release']if tests else[], 'independentGateAccepted':False}
 groups['CDR14']['externalEvidence']=['accounting-qualification.json','qualified-layouts.json','actual-closure-layouts.json','complete-owned-type-layout-replay.json']
 groups['CDR15']['externalEvidence']=['frozen-identity.json','frozen-runtime-results.json']
 groups['CDR16']['externalEvidence']=['compiler-checks.json','qualified-layouts.json','complete-owned-type-layout-replay.json']
 c.save('repair-group-results.json',groups)
 # All compiler and runner sources, including rejected attempts, remain replayable.
 archive_map={}
 for p in h.glob('*-source-manifest.json'):
  a=p.with_name(p.name.replace('-source-manifest.json','-source.tar.gz'))
  if a.exists():archive_map.setdefault(c.sha(p.read_bytes()),[]).append({'manifest':p.name,'archive':a.name})
 commands=[]
 for p in sorted((h/'commands').glob('*/receipt.json')):
  r=json.loads(p.read_text());assert r['sourceUnchanged']and not r['groupCleanup']['after']and r['sourceTreeBeforeSHA256']in archive_map
  r['receipt']=str(p.relative_to(h));commands.append(r)
 c.save('commands.json',commands)
 c.save('command-source-retention.json',[{'receipt':r['receipt'],'sourceSHA256':r['sourceTreeBeforeSHA256'],'archives':archive_map[r['sourceTreeBeforeSHA256']]}for r in commands])
 failed=[{'receipt':r['receipt'],'exitCode':r['exitCode'],'sourceSHA256':r['sourceTreeBeforeSHA256'],'status':'retained-nonqualifying'}for r in commands if r['exitCode']!=0]
 c.save('failed-attempts.json',failed)
 c.save('runtime-results.json',runtime)
 before=c.manifest(c.source('baseline'));after=c.manifest(c.source('candidate'))
 changes={n:{'before':before.get(n),'after':after[n]}for n in after if before.get(n)!=after[n]};c.save('changed-files.json',changes)
 # The patch is a source artifact; Git is not invoked or mutated by this lane.
 import difflib
 patch=''
 for n in changes:
  patch+=''.join(difflib.unified_diff((c.source('baseline')/n).read_text().splitlines(True),(c.source('candidate')/n).read_text().splitlines(True),fromfile='a/vm/'+n,tofile='b/vm/'+n))
 (h/'candidate.patch').write_text(patch)
 receipt={'schema':1,'observedUTC':c.now(),'status':'isolated-producer-candidate-independent-review-pending','acceptedBaselineSourceSHA256':'7ee6194584a5029ff2bbbcb94f8286295411cb3441a04db30c8fd4036d851329','candidateSourceSHA256':source,'sourceFiles':128,'sourceRevisionContext':'11133e60551c46c9ea3aa4eac7356ea32d44fc72','reportedRootCheckpointContext':'2e1931b4','sourceBytesAreAuthority':True,'newPositivePositions':5516,'compilerBodies':32,'priorPositionsPreserved':{'host':4876,'growth':10356,'memory':4800,'bulk':4324},'legacyMIRBodiesUnchanged':24,'oldTypeDeclarationsExact':329,'ownerFieldsAdded':[],'publicApiChanges':[],'dependenciesAdded':[],'newChecks':[],'newWorkOrFuelDebits':[],'legacyRemovalBodyExact':True,'frozenExpandedMethodsUnchanged':39,'frozenReservationBytes':2912,'layoutContexts':16,'libraryTestExecutions':sum(x['passed']for x in runtime),'diagnosticPreprobeExecutions':68,'diagnosticTestsPerContext':17,'frozenTestExecutions':64,'libraryFeatureChecks':10,'productionClippyScopes':['swift','all'],'scopedFormattingFragments':5,'positivePermanentBytes':11168,'positiveActiveProductionBytes':493272,'positiveActiveUnitBytes':1036112,'logicalNamedObjectBoundOnly':True,'rejectedAttemptsRetained':failed,'initialMIRSelectorWasIncompleteAndRejected':True,'liveIntegrated':False,'rootAccepted':False,'independentReview':'pending','g08Accepted':False,'fullSwiftAccepted':False,'publicInvocation':False,'fullDispatcher':False,'nativeAccepted':False,'physicalPhones':'deferred-disconnected-no-attempt','publishedFieldLogQualification':False,'gaAccepted':False,'scope':'Mac host private current-invocation cleanup diagnostic; no original Swift source map, module identity, readable Swift stack, debugger or public invocation claim','bindings':{n:c.sha((h/n).read_bytes())for n in ['baseline-source-manifest.json','candidate-source-manifest.json','candidate-source.tar.gz','candidate.patch','changed-files.json','accounting-qualification.json','repair-group-results.json','runtime-results.json','frozen-identity.json','frozen-runtime-results.json','compiler-checks.json','qualified-layouts.json','actual-closure-layouts.json','complete-owned-type-layout-replay.json','input-bindings.json','failed-attempts.json','command-source-retention.json']}}
 c.save('receipt.json',receipt)
 print('Finalized candidate',source,'with',receipt['libraryTestExecutions'],'library,68 preprobe,64 Frozen executions')
if __name__=='__main__':finalize()
