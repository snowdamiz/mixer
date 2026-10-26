#!/usr/bin/env python3
"""Collect selected contracts and type-compile controls only; never open the active correction."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PRIOR=ROOT/'verification/android-editor-implementation-independent'
EXPECTED={
    'verification/android-editor-boundary-root-review/replacement-amendment.md':'b386f832479884f2487df114fb080f14ebac99c747208bffd0428477c32d844b',
    'verification/android-editor-boundary-root-review/replacement-dispatch-amendment.md':'eb35fe8f9c9d9ee093ad0f40d687fbd2b4fb4382dc32cd7a74acbcc98c5da6ff',
}
INPUTS=[
    'AGENTS.md','mixer-product-plan.md',*EXPECTED,
    'verification/android-editor-implementation-independent/audit-seal.json',
    'verification/android-editor-implementation-independent/actual-review/review.md',
    'verification/android-editor-implementation-independent/actual-review/findings-1/findings-notes.md',
    'verification/android-editor-implementation-independent/actual-review/findings-1/IndependentEditorReviewTests.java',
    'verification/android-editor-implementation-independent/actual-review/findings-1/MetadataReentryControls.java',
    'verification/android-editor-implementation-independent/descriptor-expectations.json',
    'verification/android-editor-implementation-independent/replacement-preaccess/EditText.android-16.0.0_r1.java',
    'verification/android-inputconnection-authority-audit/official/aosp36/TextView.java',
    'verification/android-editor-cleanup-contract/official/View.java',
    'verification/android-editor-cleanup-contract/official/EditorInfo.java',
    *['verification/android-editor-implementation-independent/actual-review/frozen/source/'+name+'.java' for name in (
        'NativeAppearanceViewsV2','NativeRenderer','NativeCoordinatorV2','NativeOwnerV2','OwnerLifecycleV2','NativeEditorConnectionV2')],
]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    prior_bytes=(PRIOR/'audit-seal.json').read_bytes()
    assert sha(prior_bytes)=='c4db2ee776cac85b4a9589d10826fdfda519f7d16e627e4b8df86f837c8047ee'
    prior=json.loads(prior_bytes)
    for row in prior['members']:
        data=(PRIOR/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256'],row['path']
    inputs=[]
    for relative in INPUTS:
        assert not relative.startswith('verification/android-editor-replacement-implementation/')
        data=(ROOT/relative).read_bytes()
        if relative in EXPECTED:assert sha(data)==EXPECTED[relative]
        target=HERE/'inputs'/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        inputs.append({'path':relative,'bytes':len(data),'sha256':sha(data)})
    official=json.loads((HERE/'official/collection.json').read_text())
    for row in official['sources']:
        data=(HERE/row['path']).read_bytes();assert len(data)==row['bytes'] and sha(data)==row['sha256']
    jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
    sdk=Path('/opt/homebrew/share/android-commandlinetools/platforms/android-37.0/android.jar')
    assert sha(sdk.read_bytes())=='bf1b4387cc7ca94fc6ef684f040d9d16fbf16248e181819f020736ea2053f177'
    attempt=1
    while (HERE/('syntax-attempt-'+str(attempt))).exists():attempt+=1
    output=HERE/('syntax-attempt-'+str(attempt));output.mkdir();classes=output/'classes';classes.mkdir();empty=output/'empty';empty.mkdir()
    source=output/'ReplacementReviewControls.java';source.write_bytes((HERE/'ReplacementReviewControls.java').read_bytes())
    baseline_classes=PRIOR/'actual-review/frozen/runs/host-1/classes'
    env=dict(os.environ)
    for key in ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS'):env.pop(key,None)
    commands=[]
    for label,argv in [
        ('javac-version',[jdk/'bin/javac','-version']),
        ('java-version',[jdk/'bin/java','-version']),
        ('compile-control-only',[jdk/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none','-sourcepath',empty,'-cp',str(baseline_classes)+os.pathsep+str(sdk),'-d',classes,source]),
    ]:
        result=subprocess.run(list(map(str,argv)),cwd=HERE,env=env,capture_output=True,text=True,timeout=35,check=False)
        (output/(label+'.stdout.txt')).write_text(result.stdout);(output/(label+'.stderr.txt')).write_text(result.stderr)
        commands.append({'label':label,'argv':list(map(str,argv)),'exit':result.returncode,'stdout_sha256':sha(result.stdout.encode()),'stderr_sha256':sha(result.stderr.encode()),'owned_child_exited':True})
    (output/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
    receipt={
        'schema':1,'at':datetime.datetime.now(datetime.UTC).isoformat(),'argv':sys.argv,'python':sys.version,
        'context_revision_supplied_earlier_by_root':'db6332d4c27efec4f9e22b9adc43000d48c591a1',
        'revision_context_only_hashes_authoritative':True,
        'script_sha256':sha(Path(__file__).read_bytes()),'control_source_sha256':sha(source.read_bytes()),
        'inputs':inputs,'official_extra_sources':official,
        'prior_audit_members_verified_unchanged':len(prior['members']),
        'prior_audit_seal_sha256':sha(prior_bytes),
        'syntax_attempt':output.name,'commands':commands,
        'control_compilation_passed':commands[-1]['exit']==0,
        'compilation_scope':'Independent test source type-check only against immutable prior baseline class types and pinned SDK; annotation processors disabled',
        'active_correction_candidate_reads':0,'active_correction_candidate_executions':0,
        'baseline_or_correction_product_method_invocations':0,'full_source_suite_executions':0,
        'actual_source_control_groups':15,'prepared_harness_entries':6,'all_behavioral_checks_status':'pending_root_frozen_release',
        'policy_changes':['exact EditorInfo runtime class pre-effect admission','ordinary unfocused ACTION_SET_TEXT source parity','post-super one event includes same/empty','renderer-wide new-entry exclusion','end failure preserves first fatal and retains busy reservation'],
        'cleanup':'All exact finite version/javac children exited within 35-second bounds; no product JVM/fixture run, native/capture process or process inventory',
        'git_canonical_prior_audit_root_metadata_or_external_service_mutation':False,
        'decision':'preaccess_only_await_root_frozen_correction',
    }
    (HERE/'preaccess-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'prior_members_unchanged':len(prior['members']),'control_compile_exit':commands[-1]['exit'],'candidate_reads':0,'candidate_executions':0,'product_method_invocations':0}))


if __name__=='__main__':main()
