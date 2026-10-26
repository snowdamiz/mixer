#!/usr/bin/env python3
"""Finalize independent C5 evidence; no product execution or historical harness imports."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
from validate_matrix_traces import expand
HERE=Path(__file__).resolve().parent
OUT=HERE/'final-evidence'
OUT.mkdir(exist_ok=True)
HELPERS={'NativeRenderer:L238:C9:1','NativeAppearanceViewsV2:L468:C40:1','NativeAppearanceViewsV2:L518:C17:1','introduced:NativeAppearanceViewsV2/Group:onLayout(boolean,int,int,int,int):onLayout'}
PENDING='NativeRenderer:L238:C9:1'
def record(p):
 b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(p.read_text())
def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')

def callees():
    tables={}
    for p in sorted((HERE/'matrix-execution-1').glob('01-bytecode-*.stdout')):
        assert read(p.with_suffix('.command.json'))['exit_code']==0
        current=None;header=''
        for line in p.read_text().splitlines():
            m=re.match(r'^.*?\bclass (dev\.mixer\.android\.[^ <]+)(?:<[^>]+>)?(?: extends ([^ <]+))?',line)
            if m:
                current=m[1];tables[current]={'parent':m[2], 'methods':set(), 'javap':str(p.relative_to(HERE))}
            if line.startswith('  ') and not line.startswith('    ') and '(' in line and line.endswith(';'):header=line.strip()
            if current and line.strip().startswith('descriptor: ('):
                desc=line.strip().split(': ',1)[1];name=header.split('(',1)[0].split()[-1]
                name='<init>' if name==current else name.rsplit('.',1)[-1]
                tables[current]['methods'].add((name,desc))
    bindings=read(HERE/'matrix-frame-bindings.json')['selected'];rows=[]
    for row in bindings:
        comment=row['instruction'].split('// ',1)[1]
        assert comment.startswith(('Method ','InterfaceMethod '))
        target=comment.split(' ',1)[1];qualified,desc=target.split(':',1)
        if '.' in qualified:owner,name=qualified.rsplit('.',1);owner=owner.replace('/','.')
        else:owner=row['class_name'];name=qualified
        name=name.strip('"');chain=[];resolved=owner
        if name!='<init>':
            while resolved in tables and (name,desc) not in tables[resolved]['methods']:
                chain.append(resolved);resolved=tables[resolved]['parent']
                assert resolved is not None,(row['id'],owner,name,desc)
        if name=='<init>':
            kind='opaque product constructor' if owner in tables else 'opaque platform constructor'
            timing='selected constructor invocation observed through entered platform constructor; guarded product construction and caller postcheck are source-bound; no direct constructor method entry/return claim'
        elif resolved=='dev.mixer.android.NativeBridge':
            kind='mechanical JNI substitute';timing='exact selected leaf entry/beforeReturn'
        elif resolved in tables:
            kind='actual product helper';assert row['id'] in HELPERS,(row['id'],resolved,name,desc)
            timing='seven direct official-JDK JDI invoke/actual ENTRY/RETURN rows; original nested rows complementary without duplicate credit'
        else:
            assert resolved.startswith(('android.','java.')),resolved
            kind='platform method (including inherited platform dispatch)';timing='exact selected mechanical leaf entry/beforeReturn; framework internals may continue inside the already-entered call'
        rows.append({'id':row['id'],'selected_invocation':row,'symbolic_owner':owner,'method':name,'descriptor':desc,
            'inherited_product_receiver_chain':chain,'resolved_declaring_boundary':resolved,'classification':kind,'timing_evidence':timing})
    actual={r['id'] for r in rows if r['classification']=='actual product helper'}
    assert actual==HELPERS and len(rows)==189
    result={'scope':'Exhaustive189 selected callee classification from unmodified compiled method declarations, hierarchy and exact invoke instructions; classification is not implementation acceptance',
        'counts':dict(Counter(r['classification'] for r in rows)), 'actual_product_helpers':sorted(actual),
        'source_identity':'matrix-frame-bindings.json','rows':rows}
    write('callee-classification.json',result)
    return result

def identity(frame):
    head,pos=frame.rsplit('@',1);qualified,desc=head.split('(',1);name,method=qualified.rsplit('#',1)
    return name,method,'('+desc,int(pos.split(':')[0])

def tails():
    counts=Counter();rows=[];unknown=[]
    cleanup={('dev.mixer.android.NativeEnvironmentV2$Observer','cleanupAll'),('dev.mixer.android.NativeOwnerV2','removeWork'),('dev.mixer.android.NativeRenderer','disposeV2'),('dev.mixer.android.NativeRenderer','cancelInputV2'),('dev.mixer.android.NativeAppearanceViewsV2$NativeSwitch','clearTouch')}
    sites={r['id']:r for r in read(HERE/'selected-site-input-map.json')['sites']}
    for batch in [2]:
        for path in sorted((HERE/f'matrix-execution-{batch}').glob('02-*.stdout')):
            for line in path.read_text().splitlines():
                if not line.startswith('{'):continue
                row=json.loads(line)
                if 'variant' not in row or row['id'] in HELPERS:continue
                current=Counter();unresolved=[];exact=(row['class'],row['method'],row['descriptor'],row['bci'])
                for prefix,stack in expand(row['orderedTrace']):
                    if not prefix.endswith('/entry'):continue
                    frames=[identity(f) for f in stack];top=frames[0] if frames else None;native=prefix.removesuffix('/entry')
                    if row['variant']=='clean':kind='clean control'
                    elif not frames:kind='external host action without product frame'
                    elif (top[0],top[1]) in cleanup:kind='consumed independent cancellation/disposal/unregister slot'
                    elif native=='NativeBridge.destroy' and top[:2]==('dev.mixer.android.NativeCoordinatorV2','disposeOnce'):kind='consumed known session disposal'
                    elif native=='NativeBridge.abortV2' and top[:2]==('dev.mixer.android.NativeCoordinatorV2','transact'):kind='known engine-token failure abort'
                    elif row['variant'].endswith('throw-after-callback') and any(f[:2] in [('dev.mixer.android.NativeRenderer','restoreV2'),('dev.mixer.android.NativeRenderer','restoreParentV2')] for f in frames):kind='original transaction rollback after known disposition'
                    elif top==exact:kind='already-entered selected platform call continuation'
                    elif sites[row['id']]['kind']=='constructor' and exact in frames and top[1]=='<init>' and top[3]==2:kind='opaque product constructor superclass continuation'
                    elif native=='Drawable.invalidateSelf' and top[:2]==('dev.mixer.android.NativeAppearanceViewsV2$ControlDrawable','onStateChange') and exact in frames:kind='drawable work within entered platform setter'
                    elif row['variant'].startswith('dirty') and row['before']['operationPresent']:kind='same captured transaction after lifecycle-only dirty'
                    else:kind='unresolved';unresolved.append({'native':native,'frames':stack})
                    current[kind]+=1;counts[kind]+=1
                rows.append({'id':row['id'],'variant':row['variant'],'raw':str(path.relative_to(HERE)),'entry_counts':dict(current)})
                if unresolved:unknown.append({'id':row['id'],'variant':row['variant'],'entries':unresolved})
    assert len(rows)==1295
    write('tail-disposition.json',{'scope':'Ordered tail source classification of1295 direct leaf/opaque rows, with cleanup classified before dirty-transaction continuation',
        'categories':dict(counts),'rows':rows,'unresolved':unknown,
        'JDI28':'All28 direct scope/return/exception identity and debuggee tail assertions are separately sealed in jdi-helper/verification.json; no double count.',
        'nested28':'Complementary only. The old classifier one unresolved nested Group/layout row is not direct matrix credit.',
        'residual_entered_platform_disposition':'After terminal reentry, an already-entered ScrollView.layout may call child.layout before returning. The trace retains the original entered product-frame BCI; the next actual Group.onLayout acquires/validates its captured Mutation and refuses expired authority. No new Mixer setter is authorized by the framework continuation. Host evidence does not prove Android native internals.',
        'limitations':['Classifier is a source-bound explanation of observed trace tails, not a standalone authority oracle','Dirty transaction allowance applies only lifecycle-only pause with unchanged captured environment; real Observer generation invalidation has separate stale-capture failure controls','F09 independent retained-primary defect remains unresolved']})
    return len(unknown)

def objects(p):return [json.loads(line) for line in p.read_text().splitlines() if line.startswith('{')]
def matrix_credit():
 traces=read(HERE/'matrix-trace-integrity.json');jdi=read(HERE/'jdi-helper/verification.json');required={(r['id'],v) for r in read(HERE/'matrix-frame-bindings.json')['selected'] for v in ['clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback']}
 direct={(r['site_id'],r['variant']):r for r in jdi['rows']};leaf={(r['id'],r['variant']):r for r in traces['rows'] if r['id'] not in HELPERS};assert len(direct)==28 and len(leaf)==1295 and set(direct)|set(leaf)==required and len(required)==1323
 result=dict(scope='Exact immutable C5 refreshed host callback matrix; bounded private development only',required_sites=189,baseline_sites=184,introduced_sites=5,required_rows=1323,original_lossless_rows=1323,original_assertions_including_nested_rows=traces['assertions'],qualified_unique_rows=1323,direct_leaf_or_opaque_rows=1295,direct_leaf_or_opaque_assertions=sum(r['assertions'] for r in leaf.values()),direct_JDI_rows=28,JDI_controller_assertions=jdi['JDI_controller_assertions'],JDI_debuggee_assertions=jdi['JDI_debuggee_assertions'],remaining_direct_rows=0,complementary_nested_rows=28,qualified=[dict(id=key[0],variant=key[1],mechanism='exact mechanical leaf/opaque constructor boundary',**row) for key,row in leaf.items()]+[dict(id=key[0],mechanism='official JDK JDI exact selected invocation/actual helper entry/RETURN',**row) for key,row in direct.items()],native_runtime_qualified=False)
 write('matrix-credit.json',result);return result

def remaining():
 expected={'IME':168,'cancellation':32,'clearTouch':13,'reports':24,'self-causes':6,'decoders':28,'history-core':63,'history-observer':115,'history-coordinator':65};rows=[];cases=[]
 for mode,count in expected.items():
  path=HERE/'remaining-decoders-final/02-run.stdout' if mode=='decoders' else next((HERE/'remaining-final-3').glob('02-*-'+mode+'.stdout'))
  command=read(path.with_suffix('.command.json'));assert command['exit_code']==0 and command['forced_termination'] is None
  values=objects(path);result=values[-1];actual=[r for r in values if r.get('passed')];assert result['cases']==len(actual)==count
  keys={(r['family'],r['name'],r['variant']) for r in actual};assert len(keys)==count
  rows.append(dict(**result,evidence=str(path.relative_to(HERE)),command=str(path.with_suffix('.command.json').relative_to(HERE))))
  cases += [dict(**r,evidence=str(path.relative_to(HERE))) for r in actual]
 assert len(cases)==514 and len({(r['family'],r['name'],r['variant']) for r in cases})==514
 result=dict(scope='Final independently authored continuation; actual14 plus unchanged admitted leaf3, no product replacements',cases=514,assertions=sum(r['assertions'] for r in rows),families=rows,exact_case_keys=cases,final_source=record(HERE/'IndependentRemainingReview.java'),row_completeness_required=True,earlier_final1_final2_cancellation29_claims_superseded=True)
 write('remaining-host-obligations.json',result);return result

def obligations():
 previous=read(HERE.parent/'implementation-review-3/final-evidence/source-obligations.json')['families'];entries=[]
 evidence={
 'I01':'owner-contract-1 registrationReentry; history-observer twoPhase-clean/reentry; matrix initial terminal; core late-acquire controls',
 'I02':'owner-contract-1 29 main-before-stale entries; history-core 18 actual core entries+constructors/retired completion; history-observer 15 callback/capture entries+constructor',
 'I03':'owner-contract-1 readiness six variants; targeted-1 lifecycle/fresh-input; history-core readiness/temporarySize/pauseFocusConfig',
 'I04':'owner-contract-1 all8 acquisition/removal x entry/return x ordinary/fatal; history-observer64 reentry axes+all-failed removals9',
 'I05':'owner-contract-1 observerProvenance; history-observer registered-unbound/once register; typed-report foreign/null source/cause controls; actual captured source identity',
 'I06':'matrix direct1323; helper JDI28 authentic Mutation/token; targeted-1 five completion modes; history-core foreign/duplicate/resource replacement',
 'I07':'matrix constructor/default paths; all189 actual source/descriptor/BCI bindings; opaque constructor scope accurately retained',
 'I08':'matrix-credit.json:1323 unique direct rows=1295leaf/opaque+28JDI; no pending direct helper row; original nested28 complementary only',
 'I09':'targeted-1 observer-dirty/active-lifecycle-dirty/completion-dirty; matrix lifecycle-only dirty; history-coordinator abort statuses after actual generation invalidation; history-observer registration invalidation',
 'I10':'helper JDI28 original authentic scope/token; targeted-1 helper-negative13families x stale LIVE/CLEANUP; owner-contract-1 successorScope',
 'I11':'matrix scroll/navigation/gesture clean; IME18 signatures exact/successor; actual operation null normal callbacks retained',
 'I12':'remaining IME168:18 forwarding signatures x8 including actual Editable/TextWatcher/core successor;6 refusals x4 zero-forward; original matrix includes selected acquisition calls',
 'I13':'remaining cancellation32 current/pending recursive dirty/terminal/direct-renderer and MAX serial; owner-contract-1 serial/interaction/core/Observer exhaustion',
 'I14':'remaining cancellation32: first/middle/last cancelable actual Record positions, current/pending-target/detached stable authentic claims/duplicates; recursive dirty/terminal and MAX; source fixed4096 arrays bound<=12288 references',
 'I15':'remaining clearTouch13: three attempts x entry/return x ordinary/fatal12 plus actual A/E/B; real DOWN+MOVE retained parent; recursive cancel and parent-release-once',
 'I16':'repair-priority-2 exact F09+earlier owner P/F+repeated close5/54; history-coordinator four disposal phase pairs; actual clearTouch A/E/B and all8 Observer cleanup-fatal positions',
 'I17':'typed-report24 all6causes x null/ordinary/fatal/distinctP/F, foreign/null cause, stale/repeated; actual self-causes6; main/stale guard/source active-report tail',
 'I18':'actual self-causes6 originating APIs: interaction/capture/rollback/current-fatal/cancellation/direct terminal validation; actual cleanup/report/queued tail',
 'I19':'targeted-1 post/reentry/failure/terminal; self-causes authentic queued terminal close; history-core boundedLongRun5000 real refreshes; source single Work slot',
 'I20':'targeted-1 post-failure/post-reentry entry/return/remove-fatal; original exact stale work identity and consumed cancellation tokens retained',
 'I21':'matrix terminal/fatal reentry; cancellation pending-terminal cases observe actual operation retained/no invented close token, then true unwind disposes once; core pending never-return observation and matching completion',
 'I22':'source/bytecode commitV2 status0 -> direct finishV2 scalar/reference swaps -> committedPacket assignment; commitFinish scalar finally; targeted-1 completion clean/dirty/terminal/ordinary/fatal',
 'I23':'history-coordinator exact retained bytes, raw input copy detachment/signed-bit token and zero prepare/commit/abort refresh; targeted-1 retained-refresh and lifecycle dirty',
 'I24':'IME actual synchronous successors18; accepted/fresh input targeted controls; history-coordinator actual busy owner nativeInput refusal at4 executable seams; no queue/replay field by actual source',
 'I25':'targeted-1 completion-ordinary/fatal real unchanged-core fallback; actual matching/foreign/duplicate cleanup tokens and maximal serial; no fabricated token',
 'I26':'history-coordinator known1..7/unknown-1/8/MAX initial/input20; abort statuses9; acquisition failures5; actual refresh failures6; matrix attachment/restore/rollback; disposal phase pairs and F09',
 'I27':'independent descriptor15 negatives including resource/font/profile/geometry/byte/encoding, packet12 negatives; actual installed/Json/UiPacket before view construction/add/commit; real positive layout/input1',
 'I28':'v1-positives-1 five exact separate unchanged V1 positive sites; printed assertions8 static, no measured-count credit',
 'I29':'all311 admitted source hashes verified; actual14+74source leaf/probe strict explicit closure; only selected owner changed; core byte exact;189 class/source/descriptor/BCI bindings unchanged',
 'I30':'official host JDK tool hashes/versions and strict release17 evidence; root-admitted source-pair.3 literal profile retained; no consumer/SDK/D8/native runtime run by this independent lane'
 }
 limits={
 'I01':'Late native fixture constructor/factory fault execution remains source-only/native-pending.',
 'I02':'Comprehensive listed owner/core/Observer entries executed; every other package helper entry is source-reviewed, not an exhaustive arbitrary direct-call claim.',
 'I04':'Historical replacement focus/resolver targets are source-only/native-pending; exact original/dead target controls do not receive replacement credit.',
 'I07':'Opaque constructor timing is entered-platform/superclass plus guarded actual caller source, not a direct constructor method entry/return claim.',
 'I14':'Host stable-roster/fixed-limit source and actual claims; no maximal4096 real Android runtime stress or OS reclamation qualification.',
 'I18':'Each enum originating cause executed; no claim of every possible RuntimeException/Error Cartesian allocation state.',
 'I21':'Never-returned native/JNI work remains explicitly pending; no host latch/timer invents native completion or reclamation.',
 'I25':'Core decision/token allocation OOM and every arbitrary allocation site remain source-only; only admitted completion fault seam executed.',
 'I26':'Actual JNI before/after engine effects and store/runtime semantics unqualified by mechanical counted leaves.',
 'I27':'Bounded independently authored malformed corpus, no exhaustive decoder state-space or arbitrary OOM claim.',
 'I29':'311source custody includes SDK/default/V1 routing identities as root admission; this independent lane does not independently re-review all311 bodies.',
 'I30':'Official SDK/D8/Swift-JNI producer provenance remains separate; native simulator/emulator/physical/capture paused. PublicV2, published FieldLog, signing/store/operations/accountable GA pending.'
 }
 for old in previous:
  key=old['id'];entries.append(dict(id=key,name=old['name'],status='bounded selected host/source review closed; stated native/source-only limits remain pending',evidence=evidence[key],remaining_or_limit=limits.get(key,'Android framework/native runtime/accessibility/performance qualification remains pending.')))
 assert len(entries)==30
 write('source-obligations.json',dict(scope='All30 sealed preaccess families explicitly reconciled with C5 observed evidence; no family label implies exhaustive/native/GA acceptance',families=entries,implementation_recommendation='Accept exactC5 for bounded private development slice after root packet review; preserve stated pending gates',full_product_or_publicV2_or_GA_acceptance=False))

def custody_commands():
 byhash={}
 for p in HERE.rglob('*'):
  if p.is_file():byhash.setdefault(record(p)['sha256'],[]).append(str(p.relative_to(HERE)))
 commands=[];missing=[];failures=[]
 for p in sorted(HERE.rglob('*.command.json')):
  if p.is_relative_to(HERE/'candidate-5'):continue
  command=read(p);bound=[]
  for name,value in command.get('source_map',{}).items():
   candidates=byhash.get(value['sha256'],[])
   if not candidates:missing.append(dict(command=str(p.relative_to(HERE)),source=name,expected=value))
   else:bound.append(dict(source=name,sha256=value['sha256'],retained_candidates=candidates[:3]))
  mapdigest=hashlib.sha256(json.dumps(command.get('source_map',{}),sort_keys=True,separators=(',',':')).encode()).hexdigest()
  is_pair='children' in command;failed=(command.get('forced') is not None or any(c['exit_code'] for c in command['children'].values())) if is_pair else command.get('exit_code',0)!=0 or command.get('forced_termination') is not None
  row=dict(command=str(p.relative_to(HERE)),literal_argv=command.get('argv'),owned_pair_argv={n:c['argv'] for n,c in command.get('children',{}).items()},source_tree_digest=mapdigest,source_input_bindings=bound,failed=bool(failed))
  commands.append(row)
  if failed:failures.append(dict(command=str(p.relative_to(HERE)),exit_code=command.get('exit_code'),forced=command.get('forced',command.get('forced_termination')),final_credit=0))
 assert not missing,missing[:6]
 cleanups=[]
 for p in sorted(HERE.rglob('cleanup.json')):
  if p.is_relative_to(HERE/'candidate-5'):continue
  value=read(p);assert value.get('exclusive_scratch_removed') and (value.get('owned_children_reaped') or value.get('owned_exact_pids_reaped'))
  cleanups.append(dict(path=str(p.relative_to(HERE)),**value))
 assert not any(p for p in HERE.iterdir() if p.is_dir() and 'scratch' in p.name)
 write('commands-and-custody.json',dict(scope='Independent commands only; copied producer provenance excluded from pass counts',source_revision_context_only=read(HERE/'custody.json')['context_revision_only'],source_map_sha256=record(HERE/'candidate-5/source-map.json')['sha256'],commands=commands,commands_count=len(commands),source_bytes_missing=missing,preserved_failed_commands=failures,cleanup_receipts=cleanups,all_owned_scratch_removed=True,native_capture_UI_process_discovery_started=False))
 return len(commands),failures

def main():
 matrix=matrix_credit();callees();tails();rest=remaining();obligations();commands,failures=custody_commands()
 target=[]
 for path in sorted((HERE/'targeted-1').glob('03-*.stdout')):
  rows=objects(path);summary=next(r for r in rows if r.get('assertionSummary'));assert read(path.with_suffix('.command.json'))['exit_code']==0;target.append(dict(mode=summary['mode'],assertions=summary['assertions'],evidence=str(path.relative_to(HERE))))
 owner=objects(HERE/'owner-contract-1/02-run.stdout')[-1];assert owner['cases']==129
 summary=dict(candidate=5,disposition='RECOMMEND ACCEPT EXACT C5 FOR BOUNDED PRIVATE DEVELOPMENT HOST/SOURCE SCOPE; root acceptance remains separate',candidate_manifest_sha256=record(HERE/'candidate-5/manifest.json')['sha256'],source_map_sha256=record(HERE/'candidate-5/source-map.json')['sha256'],selected_owner_sha256='056aa51d07e765b59a3859ce76090477a24211c973b63336406ff4b0d4102269',core_unchanged_sha256='4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6',independent_repair_cases=5,independent_repair_assertions=54,required_matrix_sites=189,required_matrix_rows=1323,direct_qualified_rows=1323,direct_leaf_or_opaque_rows=1295,direct_JDI_rows=28,nested_complementary_rows=28,direct_pending_rows=0,matrix_original_assertions=12298,JDI_controller_assertions=848,JDI_debuggee_assertions=202,remaining_host_cases=rest['cases'],remaining_host_assertions=rest['assertions'],prior_independent_owner_core_Observer_rerun_cases=owner['cases'],prior_independent_owner_core_Observer_rerun_assertions=owner['assertions'],targeted_modes=len(target),targeted_measured_assertions=sum(r['assertions'] for r in target),five_separate_V1_positives=5,V1_assertion_counter='printed8 static metadata, not measured count',historical_groups=35,historical_source_checksites=153,historical_counter_sum447_is_not_unique_outcomes=True,concrete_product_defects_observed_in_C5=0,original_F09_C4_failure_preserved=True,all30_preaccess_families_reconciled=True,preserved_failed_commands=len(failures),commands=commands,native_source_only_pending=['Exact historical target replacement vectors remain source-only/native-pending; final leaf3 references preserved.','Arbitrary allocation/token/packet-copy OOM and real JNI before/after effect/never-return reclamation unqualified.','Opaque constructor method entry/return and max4096 native roster stress remain scoped source/entered-platform evidence.','Official SDK/D8/Swift-JNI producer/consumer evidence is separate, not independent host passes.','Native simulator/emulator/physical/capture/UI checks paused; publicV2, published separate-repository FieldLog, signing/store/operations/accountable GA acceptance pending.'],native_or_publicV2_or_GA_accepted=False,product_or_leaf_source_modified=False,committed_or_pushed=False)
 write('summary.json',summary);write('targeted-modes.json',dict(rows=target));print(json.dumps(summary))
if __name__=='__main__':main()
