#!/usr/bin/env python3
"""Describe exact bounded frozen3 findings; never run producer tests or product code."""
from pathlib import Path
import hashlib
import json
import re
import sys

HERE=Path(__file__).resolve().parent


def record(path):
    data=path.read_bytes()
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def write(name,value):
    (HERE/name).write_text(json.dumps(value,indent=2)+'\n')


def main():
    final_runner=HERE/'attempts/008-bytecode-runner.py'
    if final_runner.exists():assert final_runner.read_bytes()==(HERE/'run_targeted_review.py').read_bytes()
    else:final_runner.write_bytes((HERE/'run_targeted_review.py').read_bytes())
    drivers={1:'001-retained-controls.java',2:'002-post-reentry-controls.java',3:'003-helper-fixture-before-diagnostics.java',
        4:'004-duplicate-generation-IndependentOwnerFocusReview.java',5:'005-helper-negative-passing.java',
        6:'006-active-lifecycle-dirty.java',7:'007-observer-refresh-terminal.java',8:'007-observer-refresh-terminal.java'}
    histories=[];executions=[]
    for number,authored in drivers.items():
        directory=HERE/f'targeted-{number}';compiled=json.loads((directory/'01-compile.command.json').read_text())
        source=HERE/'attempts'/authored;assert record(source)==compiled['source_map']['IndependentOwnerFocusReview.java']
        runner=HERE/'attempts'/('008-bytecode-runner.py' if number==8 else '001-002-targeted-runner.py')
        assert record(runner)['sha256']==compiled['independent_runner_sha256']
        inputs={name:dict(path=name,**record(HERE/name)) for name in ['independent-descriptor.json','independent-packet-1.json','independent-packet-2.json']}
        if number in [3,4,5]:
            helper=HERE/('attempts/004-duplicate-generation-independent-helper-packet.json' if number in [3,4] else 'independent-helper-packet.json')
            inputs['independent-helper-packet.json']=dict(path=str(helper.relative_to(HERE)),**record(helper))
        histories.append(dict(run=directory.name,authored_driver=dict(path=str(source.relative_to(HERE)),**record(source)),
            authored_runner=dict(path=str(runner.relative_to(HERE)),**record(runner)),runtime_inputs=inputs))
        for command in sorted(directory.glob('03-*.command.json')):
            run=json.loads(command.read_text());mode=command.name[3:].removesuffix('.command.json')
            executions.append(dict(run=directory.name,mode=mode,exit_code=run['exit_code'],command=str(command.relative_to(HERE)),
                classification='reviewer-input-setup-failure' if number in [3,4] else 'confirmed-product-boundary-failure' if number==6 else 'passing-targeted-control'))
    write('historical-authored-source-map.json',dict(schema=1,scope='Exact retained authored/input bytes for all invocations; no producer oracle',runs=histories))
    index=[]
    maps={'NativeCoordinatorV2HostTests.java':{'success':['I06','I22','I23'],'prepareAndAttachmentFaults':['I26','I27'],
        'commitDispositions':['I26'],'cleanupFaults':['I16','I26'],'nativeInputAndEnvironment':['I09','I24'],'lifecycle':['I21']},
        'NativeEnvironmentV2ObserverHostTests.java':{'twoPhase':['I04','I05'],'clean':['I04'],'acquisitionFailures':['I04'],
        'cleanupFailures':['I04','I16'],'reentry':['I04'],'lateAndThreads':['I02','I04'],'terminalsAndTargets':['I04','I05','I13']},
        'OwnerLifecycleV2HostTests.java':{'readiness':['I01','I03'],'freshProbe':['I03'],'dirtyBurst':['I09','I19'],
        'invalidationDuringOperations':['I09'],'temporarySize':['I03'],'closeBeforeReadyAndStaleQueue':['I19','I20'],
        'closeDuringOpen':['I21'],'failedOpenWithResource':['I21','I26'],'inputSerializationAndReentrantTerminal':['I06','I24'],
        'refreshDetachAndNeverReturn':['I21'],'foreignAndDuplicateCompletions':['I06'],'operationCannotReplaceResource':['I06'],
        'stalePresentationAndInputDirty':['I10','I24'],'windowRetirementMatrix':['I03'],'pauseFocusConfig':['I03','I09'],
        'failuresAndIndependentCleanup':['I16','I26'],'failedRefreshAndInput':['I26'],'overflow':['I13'],
        'recreationAndIdentityEquality':['I01','I05'],'wrongThreadEveryEntry':['I02'],'boundedLongRun':['I19'],
        'malformedFactsAndUnknownOutcome':['I03','I26']}}
    for entry in json.loads((HERE/'historical-vector-inputs.json').read_text())['inputs']:
        path=HERE/'candidate-3'/entry['path'];source=path.read_text();groups=[]
        for line,text in enumerate(source.splitlines(),1):
            declaration=re.search(r'private static void ([A-Za-z0-9_]+)\(',text)
            if declaration and declaration[1] in maps[path.name]:
                groups.append(dict(method=declaration[1],line=line,selected_families=maps[path.name][declaration[1]],
                    independent_full_vector_migration='pending',oracle='sealed selected contracts and independently authored preaccess cases'))
        index.append(dict(path=str(path.relative_to(HERE)),source=record(path),historical_group_methods=groups,
            producer_source_compiled_or_executed=False,used_as_expected_behavior_oracle=False))
    write('historical-vector-obligation-index.json',dict(schema=1,scope='Source identity and grouped historical obligation enumeration only',
        declared_historical_counts_from_root=[133,141,173],counts_independently_reexecuted=False,full_vector_expansion_and_migration='pending',sources=index))
    write('findings.json',dict(schema=1,candidate=3,candidate_manifest_sha256='c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b',
        unresolved=[dict(id='F08',status='independent-runtime-confirmed',title='Concrete gate reopened before dirty completion callback',families=['I06','I09','I19','I22'],
            sources={'NativeRenderer.java':[403,403],'NativeOwnerV2.java':[316,331]},evidence='targeted-6/03-active-lifecycle-dirty.stdout',
            failed_assertion='targeted-6/03-active-lifecycle-dirty.stderr',witness_seal_sha256='f0bf0150fed64e0e3b47da17e7432ffa1d32d1ae34f2c678b478fc6429e9f1e2',
            observation=dict(shared_authority_open=False,current_gate_open=True,actual_core_phase='LIVE',actual_core_dirty=True,queued_drains=1,commit_calls=1),
            required_repair='Scalar-close concrete gates before completion bookkeeping/queue callbacks; preserve successful lifecycle-dirty completion and clean current scalar publication outside commit-to-finish.',
            limitation='Concrete gate source-boundary deviation; no shared authority reopening or extra engine operation claimed.')],
        prior_findings=dict(F01='actual active cancellation RETURNED positive in targeted6',F02='retained focus control passes',
            F03='onResume terminal control passes; start/Work cases pending',F04='source-only independent unwind review; native runtime pending',
            F05='explicit parameter/caller source review; full live recursive positive pending',F06='retained plus3 deferred-post runtime controls pass',
            F07='13 actual helper families × stale/CLEANUP =26 before-native refusals'),
        recommendation='reject-candidate3; review repaired separately admitted candidate4',repairs_after3_reviewed=False,implementation_accepted=False))
    write('receipt.json',dict(schema=1,scope='Bounded independent frozen3 actual-source review; rejected candidate; full matrix pending',
        context_revision_from_root='137d3e1d833fcaee08244b439e50c2c42723bddd',
        candidate_manifest_sha256='c5bed3d89498abe0f9d9ee2547e74f4b26d2f29a05c9744e09b61d47259ecb6b',
        admission_sha256='81f9a86838a060063db5ffa5abd9ee63581e5032a9899a68e88165f03c5e7378',
        overriding_gate_hold_sha256='e215582b755848778b125c77dc73eb64e0195db33d8768e5e936c02daecb79cb',
        rejected_prior_review_manifest_sha256='e59aed63978371a1bb946b77b3e07ef0fce0fd9bd39a14d1c5c3f45aa2dd4742',
        actual_compile_closure=dict(subjects=14,mechanical_substitutes=73,probe=1,independent_driver=1,files=89),
        executions=executions,distinct_targeted_controls=14,distinct_controls_passed=13,confirmed_product_boundary_failures=1,reviewer_setup_failures_retained=2,
        helper_negative_families=13,helper_negative_refusals=26,helper_negative_native_leaves=0,
        exact_targeted_runtime_frames_bound=38,full_site_matrix_complete=False,full_matrix_rows_qualified=0,
        baseline_V2_sites_required=184,cases_per_site_required=7,reported_candidate_sites_from_root_producer=189,
        full_new_site_inventory_independently_bound=False,V1_positive_rows_executed=0,legacy_vector_migration_complete=False,
        legacy_sources_read_with_root_authorization=True,legacy_sources_expected_behavior_oracle=False,
        pending=['184 baseline sites ×7 and introduced sites with distinct actual descriptor/BCI/caller bindings','five separate unchanged V1 positives',
            'complete actual ClosureA/B family coverage','legacy133/141/173 vector expansion/migration','remaining helper-return and live recursive positive controls',
            'start and Work terminal readiness cases','fixed lifecycle-dirty completion and completionFault boundary on later frozen bytes',
            'full public/SDK/default/profile source qualification','root CLI consumer/build qualification','native/device/physical-phone/publicV2/GA gates'],
        tooling=dict(official_local_JDK=27,Java_release_target=17,Java_runtime=27,strict_explicit_compilation=True,version_directory='tools',python=sys.version),
        restrictions=dict(mutable_product_read=False,producer_harness_model_or_runner_executed=False,producer_tests_used_as_oracle=False,
            CLI_lane_read_or_edited=False,native_runtime=False,UI=False,capture=False,process_discovery=False,external_dependencies_installed=False,
            git_actions=False,root_metadata_edited=False,later_repairs_read=False),
        cleanup=dict(all_observed_owned_children_returned_and_reaped=True,exclusive_scratch_absent=not(HERE/'scratch').exists()),
        implementation_accepted=False,CLI_consumer_qualified=False,native_qualified=False,public_V2_enabled=False,GA_qualified=False))
    print(json.dumps(dict(status='frozen3-bounded-rejection-recorded',actual_runtime_invocations=len(executions),full_matrix_complete=False)))


if __name__=='__main__':main()
