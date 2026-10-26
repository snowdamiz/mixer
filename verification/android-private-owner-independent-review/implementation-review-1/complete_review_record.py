#!/usr/bin/env python3
"""Describe retained candidate2 evidence without rerunning product code."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def record(path):
    data = path.read_bytes()
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


def main():
    # Archive exact final runner before sealing. Older bytes are never replaced.
    archive = HERE / 'attempts/008-final-bytecode-runner.py'
    if archive.exists():
        assert archive.read_bytes() == (HERE / 'run_targeted_review.py').read_bytes()
    else:
        archive.write_bytes((HERE / 'run_targeted_review.py').read_bytes())
    drivers = {}
    for path in sorted((HERE / 'attempts').glob('*.java')):
        drivers[record(path)['sha256']] = path
    runners = {1:'001-targeted-runner.java-archive.py',2:'002-targeted-runner.py',
        3:'003-targeted-runner.py',4:'004-targeted-runner.py',5:'005-targeted-runner.py',
        6:'006-targeted-runner.py',7:'007-bytecode-runner.py',8:'008-final-bytecode-runner.py'}
    histories = []
    executions = []
    for directory in sorted(HERE.glob('targeted-*')):
        number = int(directory.name.split('-')[1])
        receipt = json.loads((directory / '01-compile.command.json').read_text())
        authored = receipt['source_map']['IndependentOwnerFocusReview.java']
        driver = drivers[authored['sha256']]
        assert record(driver) == authored
        runner = HERE / 'attempts' / runners[number]
        if 'independent_runner_sha256' in receipt:
            assert receipt['independent_runner_sha256'] == record(runner)['sha256']
        histories.append(dict(run=directory.name,
            compiled_driver=dict(path=str(driver.relative_to(HERE)), **authored),
            authored_runner=dict(path=str(runner.relative_to(HERE)), **record(runner))))
        for command in sorted(directory.glob('03-*.command.json')):
            run = json.loads(command.read_text())
            executions.append(dict(run=directory.name, mode=command.name[3:].removesuffix('.command.json'),
                exit_code=run['exit_code'], command=str(command.relative_to(HERE)),
                stdout=str(command.with_name(command.name.replace('.command.json','.stdout')).relative_to(HERE)),
                stderr=str(command.with_name(command.name.replace('.command.json','.stderr')).relative_to(HERE)),
                interpretation='reviewer-setup-failure' if directory.name=='targeted-1' and 'fresh-input' in command.name else
                    'expected-boundary-assertion-failure' if run['exit_code'] else 'targeted-positive-control'))
    write('historical-authored-source-map.json', dict(schema=1,
        scope='Exact authored bytes for every targeted invocation; no historical evidence overwritten', runs=histories))
    native = 'native/android/app/src/dev/mixer/android/'
    findings = [
        dict(id='F01',title='Input cancellation completion conflates unrelated coordinator activity',
            status='known-root-finding-source-corroborated',families=['I14','I16','I21'],
            source=native+'NativeOwnerV2.java',lines=[220,228],
            obligation='Returned cancellation is distinct from active/report disposal deferral.',
            evidence=['candidate-2/source/'+native+'NativeOwnerV2.java'],
            limitation='No additional independent runtime reproduction claimed.'),
        dict(id='F02',title='Fresh input focus invalidation occurs before scalar sealing',
            status='independent-runtime-confirmed',families=['I03','I06','I24'],
            source=native+'NativeOwnerV2.java',lines=[169,189],
            related_lines=[249,256],
            obligation='Scalar shared/current/pending closure precedes fresh probes, core effects and callbacks; every SEAL closes flags.',
            evidence=['targeted-2/03-fresh-input.stdout','targeted-2/03-fresh-input.stderr','targeted-3/03-fresh-input.stdout'],
            observation=dict(actual_core_dirty=True,actual_core_focused=False,draw_allowed=True,input_allowed=True,current_gate_open=True),
            limitation='Lifecycle positive seals correctly; the defect is nativeInput fresh acquisition plus ignored nonterminal SEAL.'),
        dict(id='F03',title='Ordinary readiness probes continue after actual cancellation terminal reentry',
            status='independent-runtime-confirmed-source-boundary-deviation',families=['I03','I10','I21'],
            source=native+'NativeOwnerV2.java',lines=[117,123],
            related_source_paths=[native+'NativeRenderer.java',native+'NativeCoordinatorV2.java'],
            obligation='After Gate.invalidate cancellation reenters terminal close, stop ordinary readiness probes; only consumed cleanup may continue.',
            evidence=['targeted-3/03-terminal.stdout','targeted-3/03-terminal.stderr'],
            observation=dict(actual_core_phase='RETIRED',draw_allowed=False,input_allowed=False,prepare_calls=1,destroy_calls=1),
            limitation='No reopening or new operation observed. start and Work.run source counterparts require corrected separate controls.'),
        dict(id='F04',title='Private renderer fixture/factory failure cleanup is incomplete',
            status='independent-source-only',families=['I04','I16','I26'],
            source='native/android/tests/NativeAppearanceV2Instrumentation.java',lines=[48,53],related_lines=[75,87],
            obligation='Independently unwind registered observer, renderer/core and dedicated nonprimary root; preserve first ordinary/fatal.',
            evidence=['candidate-2/source/native/android/tests/NativeAppearanceV2Instrumentation.java'],
            limitation='No native instrumentation execution or synthetic native fixture substitute; producer repair claims remain unreviewed.'),
        dict(id='F05',title='Explicit immutable Mutation helper parameters and recursive propagation missing',
            status='independent-source-only-mandatory-contract',families=['I07','I10','I11'],
            source=native+'NativeAppearanceViewsV2.java',lines=[139,139],
            signatures={'Record':139,'bind':222,'measure':389,'measureList':533,'installChildren':579,'layoutRoot':595,'layout':603},
            callers=['NativeRenderer.prepareV2','NativeRenderer.attachV2','recursive measure/measureList/layout','Group.onLayout/titleLayout','NativeScroll.onScrollChanged'],
            obligation='Selected correction lines288–298 require explicit same captured Mutation through these helpers/callers.',
            evidence=['candidate-2/source/'+native+'NativeAppearanceViewsV2.java','candidate-2/source/'+native+'NativeRenderer.java'],
            limitation='Present transactions often recapture the same retained object; no authority-minting or successor bypass claimed.'),
        dict(id='F06',title='Possibly enqueued owned Work loses identity before cancellation attempt',
            status='independent-runtime-confirmed',families=['I19','I20'],
            source=native+'NativeOwnerV2.java',lines=[318,335],
            obligation='Keep the exact possibly-enqueued owned Work until actual removeCallbacks disposition; ledger must distinguish attempt/return.',
            evidence=['targeted-5/03-post-failure.stdout','targeted-5/03-post-failure.stderr'],
            observation=dict(actual_queued_after_retirement=1,actual_remove_calls=0,handler_ledger='RETURNED',same_primary=True,actual_core_phase='RETIRED',JNIcreate=0),
            limitation='Retained stale delivery was drained and stayed inert; no authority reopening claimed.'),
        dict(id='F07',title='Ordinary helpers do not refuse CLEANUP mode explicitly',
            status='root-producer-reported-independently-source-corroborated',families=['I10'],
            source=native+'NativeAppearanceViewsV2.java',lines=[66,76],
            obligation='Selected correction limits CLEANUP to consumed release/hide, forbidding bind/layout authority.',
            evidence=['candidate-2/source/'+native+'NativeAppearanceViewsV2.java'],
            limitation='No production Mutation.cleanup caller exists in this frozen candidate. No reached production bypass or independent runtime proof claimed.')]
    write('findings.json',dict(schema=1,candidate=2,candidate_manifest_sha256='dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7',
        recommendation='reject-candidate2-for-implementation-acceptance; review repaired frozen candidate separately',
        findings=findings,repairs_reviewed=False,implementation_accepted=False))
    cases = json.loads((HERE.parent/'preaccess/cases.json').read_text())
    write('receipt.json',dict(schema=1,scope='Bounded independent frozen candidate2 actual-source review; incomplete qualification',
        context_revision_from_root_admission='5c1cf075be26b7a71297552723861ef893e69e7d',
        candidate_manifest_sha256='dc75c6544fdc10d25457c00782dcfb8afbcde756988ce0fd742606bb69c8c0e7',
        admission_sha256='77f257671008d2d6dc51530b8b3d3f954c4ce3f75eeb9edc6257a3b10805df42',
        overriding_hold_sha256='f719fe06f8e162ab99de087157bf69a461b6a195bbdcdd79a497166d71bd9c77',
        selected_clarification_sha256='2a1574cea4d94b21bbf5d59b64484700ca7dcdf8d94fd3822fdf8fb63c5f0fa4',
        immutable_preaccess_manifest_sha256='3d9100d342756d902152a6e786ec0e2a8ae1cd63d3ca79dde68f56ce3c7a390b',
        immutable_leaf_review_manifest_sha256='a553307572c2a7384a2a9129016a629fc8dd572f451da87c6c2714ce6be34ec7',
        actual_compile_closure=dict(subjects=14,mechanical_platform_JNI_substitutes=73,probe=1,independent_test_source=1,source_files=89),
        executed_distinct_targeted_controls=['lifecycle','fresh-input','terminal','accepted-input','post-failure','registration-failure'],
        actual_host_executions=executions,
        initial_reviewer_setup_failure_retained=True,failed_product_assertions_retained=True,
        compile_only_supplementary_invocations=['targeted-7','targeted-8'],
        successful_complete_site_matrix_rows=0,
        complete_matrix_executed=False,new_site_inventory_completed=False,five_V1_positive_baselines_executed=False,
        selected_family_count=len(cases['families']),selected_baseline_V2_sites=184,selected_baseline_seven_case_rows=len(cases['baseline_v2_matrix']),
        pending=['all184 baseline IDs ×7 with distinct source/descriptor/BCI identities','all introduced site rows','five separate V1 positives',
            'full Closure A owner/core/coordinator/Observer cases','full Closure B actual14-body behavioral coverage','repaired candidate review',
            'SDK projection and descriptor/default public-boundary verification','root-selected profile/CLI integration and consumers',
            'native constructor/framework/JNI semantics','native/device and physical-phone matrix','publicV2/GA acceptance'],
        tooling=dict(official_local_JDK=27,Java_release_target=17,Java_runtime=27,strict_compile=True,empty_classpath_sourcepath=True,
            exact_sources_and_classes_recorded=True,exact_runtime_frames_bound=33,version_directory='tools',python=sys.version),
        restrictions=dict(mutable_product_read=False,producer_runners_or_models_executed=False,producer_fixtures_used_as_oracle=False,
            old_hosted_harness_read_or_run=False,native_runtime=False,UI=False,capture=False,process_discovery=False,CLI_consumers_run=False,
            external_dependencies_installed=False,git_actions=False,root_metadata_edited=False,repairs_reviewed=False),
        cleanup=dict(all_observed_owned_children_returned_and_reaped=True,exclusive_scratch_absent=not(HERE/'scratch').exists(),other_projects_untouched=True),
        source_provenance='Root admitted frozen bytes only; independent own descriptor/packets/fault oracles; exact admitted leaf3 mechanics',
        implementation_accepted=False,CLI_consumer_qualified=False,native_qualified=False,public_V2_enabled=False,GA_qualified=False))
    print(json.dumps(dict(status='candidate2-recorded-with-unresolved-findings',findings=len(findings),actual_host_invocations=len(executions),complete_matrix=False)))


if __name__ == '__main__':
    main()
