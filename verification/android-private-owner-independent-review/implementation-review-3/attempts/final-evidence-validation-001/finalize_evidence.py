#!/usr/bin/env python3
"""Record final evidence credit and explicit limits; executes no product/test code."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
from validate_matrix_traces import expand

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'final-evidence'
OUT.mkdir(exist_ok=True)
HELPERS={
    'NativeRenderer:L238:C9:1',
    'NativeAppearanceViewsV2:L468:C40:1',
    'NativeAppearanceViewsV2:L518:C17:1',
    'introduced:NativeAppearanceViewsV2/Group:onLayout(boolean,int,int,int,int):onLayout',
}
PENDING='NativeRenderer:L238:C9:1'
def record(p):
    b=p.read_bytes();return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def read(p):return json.loads(p.read_text())
def write(name,data):
    p=OUT/name;assert not p.exists();p.write_text(json.dumps(data,indent=2)+'\n')

def callees():
    tables={}
    for p in sorted((HERE/'matrix-execution-10').glob('01-bytecode-*.stdout')):
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
            timing='nested leaf only; seven direct method entry/return cases pending' if row['id']==PENDING else 'seven direct JDI invoke/RETURN cases; original nested rows complementary'
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

def matrix_credit():
    traces=read(HERE/'matrix-trace-integrity.json');jdi=read(HERE/'jdi-helper/verification.json')
    variants={'clean','terminal-at-entry','terminal-before-return','dirty-at-entry','dirty-before-return','ordinary-throw-after-callback','fatal-throw-after-callback'}
    original={(r['id'],r['variant']):r for r in traces['rows']};assert len(original)==1323
    source_ids={r['id'] for r in read(HERE/'selected-site-input-map.json')['sites']};assert len(source_ids)==189
    direct={(r['site_id'],r['variant']):r for r in jdi['rows']};assert len(direct)==21
    assert {k[0] for k in direct}==HELPERS-{PENDING}
    qualified=[];pending=[];complementary=[]
    for identifier in sorted(source_ids):
        assert {variant for site,variant in original if site==identifier}==variants
        for variant in sorted(variants):
            r=original[(identifier,variant)]
            if identifier in HELPERS:
                complementary.append({'id':identifier,'variant':variant,'raw':r['source'],'credit':0,'reason':'nested platform callback does not establish direct product helper entry/return timing'})
                if (identifier,variant) in direct:
                    qualified.append({'id':identifier,'variant':variant,'mechanism':'official JDK JDI at source-bound invoke/callee RETURN','command':direct[(identifier,variant)]['command']})
                else:pending.append({'id':identifier,'variant':variant,'reason':'Direct measure helper timing not executed; existing nested leaf row passes but receives no direct credit'})
            else:qualified.append({'id':identifier,'variant':variant,'mechanism':'exact mechanical leaf or opaque constructor boundary','raw':r['source'],'assertions':r['assertions']})
    assert len(qualified)==1316 and len(pending)==7 and len(complementary)==28
    result={'scope':'Final corrected unique callback matrix credit; implementation rejected for F09',
        'required_sites':189,'baseline_sites':184,'introduced_sites':5,'required_rows':1323,
        'original_lossless_rows':1323,'original_assertions_including_nested_rows':traces['assertions'],
        'qualified_unique_rows':len(qualified),'direct_leaf_or_opaque_rows':1295,'direct_leaf_or_opaque_assertions':sum(r.get('assertions',0) for r in qualified),
        'direct_JDI_rows':21,'JDI_controller_assertions':jdi['controller_assertions'],'JDI_debuggee_assertions':jdi['debuggee_assertions'],
        'remaining_direct_rows':7,'earlier_1302_plus_21_direct_claim_superseded':True,
        'timing_correction':'NativeRenderer:L238:C9:1 is a fourth actual product helper invocation (measure), with nested View.measure controls only. No count relaxation.',
        'qualified':qualified,'pending':pending,'complementary_without_duplicate_credit':complementary,
        'failed_attempts':'All output-limit, aggregation-only and reviewer-controller failures preserved; zero qualification credit. No producer runner/model execution.'}
    write('matrix-credit.json',result)
    return result

def identity(frame):
    head,pos=frame.rsplit('@',1);qualified,desc=head.split('(',1);name,method=qualified.rsplit('#',1)
    return name,method,'('+desc,int(pos.split(':')[0])
def tails():
    counts=Counter();rows=[];unknown=[]
    cleanup={('dev.mixer.android.NativeEnvironmentV2$Observer','cleanupAll'),('dev.mixer.android.NativeOwnerV2','removeWork'),('dev.mixer.android.NativeRenderer','disposeV2'),('dev.mixer.android.NativeRenderer','cancelInputV2'),('dev.mixer.android.NativeAppearanceViewsV2$NativeSwitch','clearTouch')}
    sites={r['id']:r for r in read(HERE/'selected-site-input-map.json')['sites']}
    for batch in [6,7,8]:
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
        'JDI21':'Direct scope/return/exception identity and debuggee tail assertions are separately sealed in jdi-helper/verification.json; no double count.',
        'nested28':'Complementary only. The old classifier one unresolved nested Group/layout row is not direct matrix credit.',
        'residual_entered_platform_disposition':'After terminal reentry, an already-entered ScrollView.layout may call child.layout before returning. The trace retains the original entered product-frame BCI; the next actual Group.onLayout acquires/validates its captured Mutation and refuses expired authority. No new Mixer setter is authorized by the framework continuation. Host evidence does not prove Android native internals.',
        'limitations':['Classifier is a source-bound explanation of observed trace tails, not a standalone authority oracle','Dirty transaction allowance applies only lifecycle-only pause with unchanged captured environment; real Observer generation invalidation has separate stale-capture failure controls','F09 independent retained-primary defect remains unresolved']})
    return len(unknown)

GROUP_EVIDENCE={
 'success':['targeted-3','owner-contract-3/02-run.stdout','final-evidence/matrix-credit.json'],
 'prepareAndAttachmentFaults':['owner-contract-3/02-run.stdout','matrix-execution-6','matrix-execution-7','matrix-execution-8'],
 'commitDispositions':['IndependentOwnerContractReview.engineDispositions: actual statuses1–8, known abort/disposition and failed joined-owner lifetime'],
 'cleanupFaults':['disposal-priority-finding/finding.json: F09 failed','IndependentOwnerContractReview.engineDispositions'],
 'nativeInputAndEnvironment':['targeted-3','IndependentOwnerContractReview.successorScope','final-evidence/matrix-credit.json'],
 'lifecycle':['targeted-3','targeted-4','IndependentOwnerContractReview.engineDispositions'],
 'twoPhase':['IndependentOwnerContractReview.registrationReentry','targeted-4 registration-failure'],
 'clean':['IndependentOwnerContractReview.observerProvenance','IndependentOwnerContractReview.readiness'],
 'acquisitionFailures':['IndependentOwnerContractReview.registration: eight slots × entry/return × ordinary/fatal'],
 'cleanupFailures':['IndependentOwnerContractReview.removal: eight slots × entry/return × ordinary/fatal'],
 'reentry':['IndependentOwnerContractReview.registrationReentry: eight slots × entry/return'],
 'lateAndThreads':['IndependentOwnerContractReview.mainAndExhaustion','targeted-4 terminal'],
 'terminalsAndTargets':['IndependentOwnerContractReview.observerProvenance','IndependentOwnerContractReview.readiness: dead original focus target'],
 'readiness':['IndependentOwnerContractReview.readiness','IndependentOwnerContractReview.actualCore'],
 'freshProbe':['IndependentOwnerContractReview.readiness','targeted-4 lifecycle/fresh-input'],
 'dirtyBurst':['IndependentOwnerContractReview.actualCore','targeted-3','final-evidence/matrix-credit.json'],
 'invalidationDuringOperations':['targeted-3 observer-stale','final-evidence/matrix-credit.json','selected dirty clarification'],
 'temporarySize':['IndependentOwnerContractReview.readiness','IndependentOwnerContractReview.actualCore'],
 'closeBeforeReadyAndStaleQueue':['targeted-4 terminal','IndependentOwnerContractReview.registrationReentry'],
 'closeDuringOpen':['IndependentOwnerContractReview.registrationReentry','final-evidence/matrix-credit.json terminal initial-operation variants'],
 'failedOpenWithResource':['final-evidence/matrix-credit.json terminal/fault initial-operation variants'],
 'inputSerializationAndReentrantTerminal':['IndependentOwnerContractReview.actualCore','targeted-3 active-cancellation','targeted-4 terminal'],
 'refreshDetachAndNeverReturn':['IndependentOwnerContractReview.actualCore','targeted-3 active-cancellation; actual nonreturning JNI not simulated'],
 'foreignAndDuplicateCompletions':['IndependentOwnerContractReview.actualCore'],
 'operationCannotReplaceResource':['IndependentOwnerContractReview.actualCore'],
 'stalePresentationAndInputDirty':['IndependentOwnerContractReview.actualCore','IndependentOwnerContractReview.successorScope'],
 'windowRetirementMatrix':['IndependentOwnerContractReview.actualCore: six actual core terminal window variants'],
 'pauseFocusConfig':['targeted-4 lifecycle/fresh-input','IndependentOwnerContractReview.actualCore'],
 'failuresAndIndependentCleanup':['IndependentOwnerContractReview.actualCore','IndependentOwnerContractReview.removal','disposal-priority-finding/finding.json failed F09'],
 'failedRefreshAndInput':['IndependentOwnerContractReview.actualCore','IndependentOwnerContractReview.engineDispositions'],
 'overflow':['IndependentOwnerContractReview.mainAndExhaustion','IndependentOwnerContractReview.observerProvenance','IndependentOwnerContractReview.actualCore'],
 'recreationAndIdentityEquality':['IndependentOwnerContractReview.actualCore','IndependentOwnerContractReview.observerProvenance'],
 'wrongThreadEveryEntry':['IndependentOwnerContractReview.mainAndExhaustion:29 actual main-before-stale entry controls; exhaustive historical entry expansion pending'],
 'boundedLongRun':['source-bound constant work slot; no independent historical long-run expansion'],
 'malformedFactsAndUnknownOutcome':['IndependentOwnerContractReview.actualCore','IndependentOwnerContractReview.engineDispositions']
}
def historical():
    old=HERE.parent/'implementation-review-2'
    index=read(old/'historical-vector-obligation-index.json');sources=[]
    for source in index['sources']:
        p=old/source['path'];assert record(p)==source['source'];text=p.read_text();lines=text.splitlines();groups=[]
        declarations=list(re.finditer(r'(?m)^    private static void (\w+)\([^\n]*\)\s*\{',text))
        for g in source['historical_group_methods']:
            start=next(m.start() for m in declarations if m[1]==g['method']);end=min([m.start() for m in declarations if m.start()>start]+[len(text)])
            body=text[start:end];checks=[]
            for m in re.finditer(r'\bcheck\s*\(',body):
                offset=start+m.start();line=text.count('\n',0,offset)+1
                # Source call-site enumeration only: labels are untrusted historical names, never expected results.
                tail=text[offset:text.find('\n',offset) if '\n' in text[offset:] else len(text)]
                labels=re.findall(r'"((?:[^"\\]|\\.)*)"',tail)
                checks.append({'line':line,'source_line_sha256':hashlib.sha256(lines[line-1].encode()).hexdigest(),'historical_label':labels[-1] if labels else None})
            migration='Preserve selected contract obligation; independently authored actual-source evidence is partial, not an unchanged historical harness pass.'
            if g['method'] in ['prepareAndAttachmentFaults','commitDispositions']:
                migration='Historical retry/session-reuse labels are deliberately migrated to selected joined-owner lifetime: any failed operation retires both owners, known statuses1–7 permit consumed abort/rollback where applicable, no retry. Actual statuses1–8 controls exercise the selected outcome; old retry expectations are not claimed passed unchanged.'
            if g['method']=='cleanupFaults':migration='Independent actual cleanup coverage finds F09 failure; the historical group is not qualified by producer counts.'
            groups.append({**g,'source_binding_only':True,'historical_check_call_sites':checks,'independent_evidence':GROUP_EVIDENCE[g['method']],
                'migration_disposition':migration,'fully_expanded_historical_dynamic_vectors':False})
        sources.append({'path':str(p.relative_to(ROOT)),'source':record(p),'historical_reported_count':{'NativeCoordinatorV2HostTests.java':133,'NativeEnvironmentV2ObserverHostTests.java':141,'OwnerLifecycleV2HostTests.java':173}[p.name],
            'execution_or_import':False,'groups':groups})
    write('historical-migration.json',{'scope':'Source-bound migration ledger of all enumerated historical groups/check call sites. Selected contracts alone supply expected behavior; no producer test/model execution, imports or oracle reuse.',
        'sources':sources,'declared_historical_counts':[133,141,173], 'counts_are_independent_passes':False,
        'full_dynamic_vector_expansion_and_one_to_one_independent_coverage':'PENDING; grouped source/check-site binding does not establish all447 dynamic vector obligations',
        'selected_retry_source_anchors':['proposal245–252: after finish active=false and exact core completion; failure retires lifetime, no retry','proposal271–274: rejected edits contained after both owners terminal'],
        'unchanged_actual_core_sha256':'4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'})

def custody_and_commands():
    custody=read(HERE/'custody.json');manifest=read(HERE/'admission/candidate-4-manifest.json')
    for row in custody['snapshot_inputs']:
        p=HERE/'candidate-4/source'/row['path'];value=record(p)
        assert value=={k:row[k] for k in ['bytes','sha256']}
        assert manifest['files']['source/'+row['path']]==value
    write('source-custody-validation.json',{'scope':'Selected immutable review inputs only; no mutable current-source comparison',
        'candidate_manifest':record(HERE/'admission/candidate-4-manifest.json'),'admission':record(HERE/'admission/candidate-4-admission.json'),
        'selected_snapshots':len(custody['snapshot_inputs']),'all_hashes_match_admitted_manifest':True,
        'actual14_plus74_source_closure':'preaccess/site-input-map.json plus admitted leaf-manifest-3.json; runtime commands list exact89 sources including one independent Java witness',
        'native_profile_inputs':'All309 full candidate input custody is the exact root admission; this lane copied94 selected bodies/support sources, not all309 for independent re-review'})
    byhash={}
    for p in HERE.rglob('*'):
        if p.is_file() and p.suffix in ['.java','.py','.json'] and not p.name.endswith('.command.json'):
            byhash.setdefault(record(p)['sha256'],[]).append(str(p.relative_to(ROOT)))
    commands=[];missing=[];version_set={}
    for p in sorted(HERE.rglob('*.command.json')):
        d=read(p);bindings=[]
        for name,value in d.get('source_map',{}).items():
            candidates=byhash.get(value['sha256'],[])
            if not candidates:
                candidate=ROOT/name
                if candidate.is_file() and record(candidate)==value:candidates=[str(candidate.relative_to(ROOT))]
            if not candidates:missing.append({'command':str(p.relative_to(HERE)),'input':name,'record':value})
            if not name.startswith('candidate-4/'):
                version_set.setdefault((name,value['sha256']),candidates)
            bindings.append({'recorded_input':name,'record':value,'retained_exact_source':candidates[0] if candidates else None})
        commands.append({'path':str(p.relative_to(HERE)),'exit_code':d.get('exit_code'),'source_bindings':bindings})
    assert not missing,missing
    sets=[];set_ids={};compact=[]
    for command in commands:
        key=json.dumps(command['source_bindings'],sort_keys=True,separators=(',',':'))
        if key not in set_ids:set_ids[key]=len(sets);sets.append(command['source_bindings'])
        compact.append({'path':command['path'],'exit_code':command['exit_code'],'source_set':set_ids[key]})
    assert [sets[r['source_set']] for r in compact]==[r['source_bindings'] for r in commands]
    write('archived-command-input-audit.json',{'scope':'Exact authored historical witness source bytes and immutable product/baseline inputs remain available for every recorded command source_map; this is evidence validation, not test execution',
        'commands':len(commands),'authored_or_tool_input_versions':len(version_set),'missing':missing,'source_sets':sets,'records':compact,'source_set_expansion_verified':True})

def main():
    callee=callees();credit=matrix_credit();unresolved=tails();historical();custody_and_commands()
    write('summary.json',{'candidate':4,'disposition':'REJECTED: confirmed F09 outer owner primary collection failure',
        'first10_controls':10,'first10_assertions':55,'additional_targeted_modes':9,
        'actual_owner_core_observer_cases':129,'actual_owner_core_observer_assertions':1787,
        'required_matrix_rows':1323,'direct_qualified_rows':1316,'direct_timing_pending_rows':7,
        'five_separate_V1_positive_sites':5,'V1_assertion_count':'Printed8 was a static label; do not treat it as measured counter',
        'direct_leaf_tail_unresolved_rows':unresolved,'actual_product_helper_sites':4,
        'historical_migration':'all enumerated historical groups/check source bindings recorded; full447 dynamic expansion/one-to-one execution pending',
        'native_or_publicV2_or_GA_acceptance':False,'candidate_source_mutations':False,
        'first10_seal':'d12dd7f879ab399900d26f5fbd559254ac495d4c4f6fe94b6430ab0ca6945087',
        'JDI21_seal':'e417e1588c8c9ebd062d047ba88f3d2f180fbbcb9bbe101361b0dbb8c46df83a',
        'F09_mini_seal':'397397444b68a6dccdbd6c5b52536e756b87467fc8d5e46771b5caf44a776a74'})
    print(json.dumps({'callee_counts':callee['counts'],'qualified_matrix_rows':credit['qualified_unique_rows'],'pending':7,'direct_tail_unresolved':unresolved}))

if __name__=='__main__':main()
