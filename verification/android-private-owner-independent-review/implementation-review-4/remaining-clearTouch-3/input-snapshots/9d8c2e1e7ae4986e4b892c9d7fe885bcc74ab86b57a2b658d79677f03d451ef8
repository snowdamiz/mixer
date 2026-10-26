#!/usr/bin/env python3
"""C5 exact-source, matrix and direct JDI credit checker. No product execution."""
from pathlib import Path
import hashlib,json,difflib
from validate_matrix_traces import expand
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'implementation-review-3'
VARIANTS={'clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'}
IDS=['NativeAppearanceViewsV2:L468:C40:1','NativeAppearanceViewsV2:L518:C17:1','introduced:NativeAppearanceViewsV2/Group:onLayout(boolean,int,int,int,int):onLayout','NativeRenderer:L238:C9:1']
def read(p):return json.loads(p.read_text())
def rec(p):
 b=p.read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def objects(p):return [json.loads(x) for x in p.read_text().splitlines() if x.startswith('{')]
def main():
 out=HERE/'checkpoint';out.mkdir(exist_ok=True)
 source=read(HERE/'candidate-5/source-map.json')
 for name,expected in source.items():assert rec(HERE/'candidate-5/source'/name)==expected,name
 changed=[]
 oldmap=read(OLD/'candidate-4/source-map.json') if (OLD/'candidate-4/source-map.json').exists() else None
 roster=read(HERE.parent/'preaccess/site-input-map.json')['concrete_subjects']+sorted(read(HERE.parent/'leaf-review-1/admission/leaf-manifest-3.json')['files'])
 for name in roster:
  before=OLD/'candidate-4/source'/name;after=HERE/'candidate-5/source'/name
  if rec(before)!=rec(after):changed.append(name);(out/(before.name+'.diff')).write_text(''.join(difflib.unified_diff(before.read_text().splitlines(True),after.read_text().splitlines(True),fromfile='admitted-C4/'+name,tofile='admitted-C5/'+name)))
 assert changed==['native/android/app/src/dev/mixer/android/NativeOwnerV2.java'],changed
 assert source['native/android/app/src/dev/mixer/android/OwnerLifecycleV2.java']['sha256']=='4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'
 binding=read(HERE/'matrix-frame-bindings.json');prior={r['id']:r for r in read(OLD/'matrix-frame-bindings.json')['selected']}
 for item in binding['selected']:
  old=prior[item['id']]
  for key in ['class_name','method','descriptor','bci','line','instruction','source_hash','compiled_class']:assert item[key]==old[key],(item['id'],key)
 jdi=[]
 for site,attempt in [(0,5),(1,5),(2,5),(3,4)]:
  directory=HERE/'jdi-helper'/f'attempt-{attempt}';codes=read(directory/'compiled-method-code-hashes.json');cleanup=read(directory/'cleanup.json');assert cleanup['owned_exact_pids_reaped'] and cleanup['exclusive_scratch_removed']
  for variant in sorted(VARIANTS):
   prefix=f'site-{site}-{variant}';command=read(directory/(prefix+'.command.json'));assert command['forced'] is None and command['owned_exact_pids_reaped'] and all(c['exit_code']==0 for c in command['children'].values())
   controller=objects(directory/(prefix+'-controller.stdout'));debuggee=objects(directory/(prefix+'-debuggee.stdout'));summary=next(v for v in controller if v.get('scope')=='exact unmodified helper breakpoint controller');result=next(v for v in debuggee if v.get('scope')=='independent exact helper invoke/return witness')
   selected=next(v for v in controller if v.get('point')=='callerPreinvoke');bind=next(v for v in binding['selected'] if v['id']==IDS[site]);assert (selected['class'],selected['method'],selected['descriptor'],selected['bci'])==(bind['class_name'],bind['method'],bind['descriptor'],bind['bci'])
   for row in controller:
    if 'method_code_sha256' in row:assert row['method_code_sha256']==codes[row['class']+'#'+row['method']+row['descriptor']]
   scopes=[v for v in controller if 'mutationID' in v];assert len({v['mutationID'] for v in scopes})==1 and len({v['actualTokenID'] for v in scopes})==1
   if 'before-return' in variant or variant=='clean':
    assert summary['calleeEntered'] and summary['returned'];ret=next(v for v in controller if v.get('point')=='calleeReturn');assert ret['bci'] in ([921,965,1008,1748,3796] if site==3 else [263] if site==0 else [221])
   if site==3:assert summary['calleeEntered'] and any(v.get('point')=='calleeEntry' and v['bci']==0 for v in controller)
   if 'throw' in variant:
    assert summary['exceptionEvents']==1
    actual=next(v for v in controller if v.get('point')=='actualThrowAt');requested=next(v for v in controller if v.get('point')=='requestedThrowAt');assert {k:v for k,v in actual.items() if k!='point'}=={k:v for k,v in requested.items() if k!='point'}
    caller=next(v for v in controller if v.get('point')=='actualThrowCaller');assert (caller['class'],caller['method'],caller['descriptor'],caller['bci'])==(bind['class_name'],bind['method'],bind['descriptor'],bind['bci']);identity=next(v for v in controller if v.get('point')=='exceptionIdentity');assert identity['requestedThrowableID']==identity['observedThrowableID']
    if site==3:assert actual['class']=='dev.mixer.android.NativeAppearanceViewsV2' and actual['method']=='measure' and actual['bci']==0
   expand(result['orderedTrace'])
   jdi.append(dict(site_id=IDS[site],site=site,variant=variant,command=str((directory/(prefix+'.command.json')).relative_to(HERE)),controller_assertions=summary['assertions'],debuggee_assertions=result['assertions'],original_mutation_id=scopes[0]['mutationID'],original_core_token_id=scopes[0]['actualTokenID'],exception_identity_verified='throw' in variant,entry_return_continuation_distinct=True))
 traces=read(HERE/'matrix-trace-integrity.json');assert traces['executed_unique_rows']==1323
 required={(r['id'],v) for r in binding['selected'] for v in VARIANTS};original={(r['id'],r['variant']) for r in traces['rows']};assert required==original
 direct={(r['id'],r['variant']) for r in traces['rows'] if r['id'] not in IDS}|{(r['site_id'],r['variant']) for r in jdi};assert direct==required and len(direct)==1323
 repair=objects(HERE/'repair-priority-2/02-run.stdout');assert repair[-1]['cases']==5
 result=dict(scope='Independent immutable C5 host checkpoint only; remaining historical work separate; native/publicV2/GA pending',source_inputs_verified=311,only_changed_actual_closure_source=changed,unchanged_core=True,selected_sites=189,source_class_descriptor_BCI_rebindings=189,original_lossless_rows=1323,original_assertions=traces['assertions'],direct_leaf_opaque_rows=1295,direct_JDI_rows=28,direct_unique_rows=1323,complementary_nested_rows=28,remaining_direct_rows=0,repair_cases=repair[-1]['cases'],repair_assertions=repair[-1]['assertions'],JDI_controller_assertions=sum(v['controller_assertions'] for v in jdi),JDI_debuggee_assertions=sum(v['debuggee_assertions'] for v in jdi),native_or_publicV2_or_GA_accepted=False)
 (HERE/'jdi-helper/verification.json').write_text(json.dumps(dict(**result,rows=jdi),indent=2)+'\n')
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 files={str(p.relative_to(HERE)):rec(p) for p in sorted(HERE.rglob('*')) if p.is_file() and (p.is_relative_to(out) or p.is_relative_to(HERE/'jdi-helper') or p.is_relative_to(HERE/'repair-priority-2')) and p.name not in ['manifest.json','manifest.sha256']}
 manifest=dict(scope='Exact repair plus complete28 direct helper checkpoint; final packet not yet accepted',members=len(files),bytes=sum(v['bytes'] for v in files.values()),files=files)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');sha=rec(out/'manifest.json')['sha256'];(out/'manifest.sha256').write_text(sha+'\n');print(json.dumps(dict(**result,checkpoint_manifest_sha256=sha)))
if __name__=='__main__':main()
