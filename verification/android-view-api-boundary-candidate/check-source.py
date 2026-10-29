#!/usr/bin/env python3
"""Filesystem/source custody only. Does not import, compile or execute subject code."""
import sys

def forbidden(*args, **kwargs):
    raise RuntimeError("pure source/data checker cannot use process/session/group/signal/timer/wait/socket operations")

def audit(event, args):
    if event.startswith(("subprocess.", "socket.", "os.exec", "os.spawn", "os.posix_spawn", "os.fork", "os.kill")):
        forbidden(event)

sys.addaudithook(audit)
# Guard available nested launch, session/group, signal, timer, wait and socket
# surfaces before filesystem inputs are read. Never imports any subject module.
import os
import subprocess
import signal
import socket
import time
import threading
import _thread
for name in ("system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "startfile",
             "kill", "killpg", "getpid", "getppid", "getpgid", "getpgrp", "getsid", "setpgid", "setpgrp", "setsid",
             "wait", "waitpid", "wait3", "wait4", "waitid", "pidfd_open"):
    if hasattr(os, name):
        setattr(os, name, forbidden)
for name in tuple(vars(os)):
    if name.startswith(("exec", "spawn")):
        setattr(os, name, forbidden)
for name in ("Popen", "run", "call", "check_call", "check_output", "getoutput", "getstatusoutput"):
    setattr(subprocess, name, forbidden)
for name in ("signal", "alarm", "setitimer", "getitimer", "pause", "raise_signal", "pthread_kill", "sigwait", "sigwaitinfo", "sigtimedwait", "pthread_sigmask", "pidfd_send_signal"):
    if hasattr(signal, name):
        setattr(signal, name, forbidden)
for name in ("socket", "socketpair", "create_connection", "create_server", "fromfd", "fromshare", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr"):
    if hasattr(socket, name):
        setattr(socket, name, forbidden)
time.sleep=forbidden
threading.Thread.start=forbidden
threading.Timer=forbidden
_thread.start_new_thread=forbidden

from pathlib import Path
import hashlib
import json
import difflib
import datetime
import traceback

D=Path(__file__).resolve().parent
ROOT=D.parent.parent
BASE=ROOT/'verification/android-editor-preservation-membership-correction/source'
CONTRACT=ROOT/'verification/android-view-api-boundary-selection-2026-10-29/contract.json'
HOST_BASE=ROOT/'verification/android-editor-preservation-membership-correction/runs/cross-2/inputs/host-leaves'

def identity(path):
    data=path.read_bytes()
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def tree(rows):
    return hashlib.sha256(''.join(name+'\0'+rows[name]['sha256']+'\n' for name in sorted(rows)).encode()).hexdigest()

def historical_tree(rows):
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    if '--verify-frozen' in sys.argv:
        frozen=json.loads((D/'freeze.json').read_text())
        manifest=json.loads((D/'manifest.json').read_text())
        assert identity(D/'manifest.json')==frozen['manifest']
        actual={str(p.relative_to(D)) for p in D.rglob('*') if p.is_file() and p.relative_to(D).parts[0]!='local'}
        assert actual=={row['path'] for row in manifest['members']}|{'manifest.json','freeze.json'}
        for row in manifest['members']:
            assert identity(D/row['path'])=={'bytes':row['bytes'],'sha256':row['sha256']},row['path']
        if (D/'local/freeze.stdout').exists():
            assert (D/'local/freeze.stdout').read_bytes()==(D/'source-check.stdout').read_bytes()
            assert (D/'local/freeze.stderr').read_bytes()==(D/'source-check.stderr').read_bytes()
        print(json.dumps({'verdict':'passed-frozen-filesystem-custody-only','freeze':identity(D/'freeze.json'),'manifest':identity(D/'manifest.json'),'derivative_product_tree':frozen['derivative_product_tree'],'member_count':manifest['member_count']},indent=2))
        return
    assert not (D/'freeze.json').exists(),'frozen packet cannot be regenerated; use --verify-frozen'
    assert identity(CONTRACT)['sha256']=='a2f0c84ea91e5df9424a702fcb4a355632b99f66f9fce8f98e4204498840adc2'
    accepted=json.loads((BASE.parent/'source-verification.json').read_text())
    before={p.name:identity(p) for p in sorted(BASE.glob('*.java'))}
    after={p.name:identity(p) for p in sorted((D/'source').glob('*.java'))}
    assert len(before)==len(after)==16 and before==accepted['source_map']
    assert accepted['product_tree']=='a5e4888b96995bf768062bd9c2f1573dc440a4fe22270a205ab5550e79f625e4'
    assert historical_tree(before)==accepted['product_tree']
    assert set(before)==set(after)
    changed=[name for name in before if before[name]!=after[name]]
    assert changed==['NativeAppearanceViewsV2.java','NativeRenderer.java'],changed
    unchanged=[name for name in before if before[name]==after[name]]
    assert len(unchanged)==14
    views=(D/'source/NativeAppearanceViewsV2.java').read_text()
    renderer=(D/'source/NativeRenderer.java').read_text()
    old_views=(BASE/'NativeAppearanceViewsV2.java').read_text()
    old_renderer=(BASE/'NativeRenderer.java').read_text()
    guard='if(Build.VERSION.SDK_INT<36)throw new AppearanceDescriptorV2.Failure(AppearanceDescriptorV2.Error.unsupportedNativeOperation);'
    assert renderer.count(guard)==old_renderer.count(guard)==1
    assert after['NativeEnvironmentV2.java']==before['NativeEnvironmentV2.java']
    # Broad accepted interval remains byte-identical, not merely free of new tokens.
    start='    void finishV2('
    assert renderer[renderer.index(start):]==old_renderer[old_renderer.index(start):]
    start='    void sealScalarV2('
    end='    Candidate prepareV2('
    assert renderer[renderer.index(start):renderer.index(end)]==old_renderer[old_renderer.index(start):old_renderer.index(end)]
    start='        Record(Context context'
    end='    private static boolean plainProposal'
    for method in ('setTextCursorDrawable','setTextSelectHandle','setTextSelectHandleLeft','setTextSelectHandleRight'):
        assert views.count('.'+method+'(')==1
        assert method not in views[views.index(start):views.index(end)]
    assert views.count('.setStateDescription(')==1 and renderer.count('.setStateDescription(')==1
    assert '.setStateDescription(' not in views[views.index('        void bind('):views.index(end)]
    assert 'v.setStateDescription(' not in renderer
    assert 'mutation.requireMutation();requireViewOperations(source);scoped=mutation;' in views
    assert 'mutation.requireMutation();requireViewOperations(next.node,next.source);editorAvailable' in views
    assert renderer.index('for(var node:plan.nodes)NativeAppearanceViewsV2.requireViewOperations')<renderer.index('new NativeAppearanceViewsV2.Record(context,source')
    v1='if(Build.VERSION.SDK_INT<30)for(UiPacket.Node n:next.nodes.values())if(n.properties.containsKey("accessibilityValue"))throw Json.bad("accessibilityValue requires API30");'
    assert v1 in renderer and v1 in old_renderer
    host={str(p.relative_to(D/'tests/host-leaves')):identity(p) for p in sorted((D/'tests/host-leaves').rglob('*.java'))}
    host_before={str(p.relative_to(HOST_BASE)):identity(p) for p in sorted(HOST_BASE.rglob('*.java'))}
    assert host==host_before
    assert identity(D/'tests/descriptor.json')['sha256']=='1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'
    cross=identity(D/'tests/cross-leaf/NativeBridge.java')
    assert cross==identity(BASE.parent/'runs/cross-2/inputs/cross-source/NativeBridge.java')
    test=(D/'tests/ViewApiBoundaryTests.java').read_text()
    assert all(token in test for token in ('new int[]{29,30,36,37}','"ordinary","fatal","stale","stale-reentry"','"entry","beforeReturn"','new int[]{28,29,30,35}','new int[]{28,29,30,36,37}'))
    patches=[]
    for name in changed:
        patches.extend(difflib.unified_diff((BASE/name).read_text().splitlines(True),(D/'source'/name).read_text().splitlines(True),fromfile='accepted/'+name,tofile='candidate/'+name))
    (D/'product.diff').write_text(''.join(patches))
    report={
        'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'verdict':'passed-pure-source-data-custody-only',
        'contract':identity(CONTRACT),'accepted_recorded_product_tree':accepted['product_tree'],
        'product_tree_algorithm':'SHA256 of source identity map JSON, sorted keys, compact separators; same as accepted baseline',
        'derivative_product_tree':historical_tree(after),
        'source_projection_algorithm':'SHA256 of sorted filename + NUL + SHA256 + LF',
        'accepted_source_projection':tree(before),'derivative_source_projection':tree(after),
        'source_members':16,'changed_product_files':changed,'unchanged_product_files':unchanged,
        'product_sources':after,'host_leaf_count':len(host),'host_leaves_byte_identical':True,
        'host_leaves_projection':tree(host),'descriptor':identity(D/'tests/descriptor.json'),
        'cross_signature_leaf':cross,'cross_signature_leaf_byte_identical':True,
        'test_source':identity(D/'tests/ViewApiBoundaryTests.java'),'product_diff':identity(D/'product.diff'),
        'preserved_checks':['observer exact file','renderer exact <36 guard','renderer finishV2 through EOF exact','renderer sealScalarV2 through prepareV2 exact','V1 property-presence refusal exact'],
        'source_topology_checks':'Later setter tokens occur only in three intended nested helpers; emitted bytecode not inspected',
        'tool':{'executable':sys.executable,'version':sys.version,'script':identity(Path(__file__))},
        'command':['python3',*sys.argv],
        'runtime_tests_run':0,'compiler_runs':0,'native_or_capture_runs':0,'subject_imports':0,
        'process_session_group_signal_timer_wait_socket_surfaces':'guarded before subject filesystem inputs; subject source never imported',
        'source_revision_context_only':'5b6fc4f5c119cb0b2770f8ee752f6cba57761229 supplied by root; no Git verification',
        'scope':'Source/data checks only. No canonical/source-pair/public V2/API28-35/native/OTA/release/GA qualification.'}
    (D/'source-check.json').write_text(json.dumps(report,indent=2)+'\n')
    output=json.dumps({key:report[key] for key in ('verdict','accepted_recorded_product_tree','derivative_product_tree','accepted_source_projection','derivative_source_projection','source_members','changed_product_files','host_leaf_count','runtime_tests_run','compiler_runs')},indent=2)+'\n'
    if '--freeze' in sys.argv:
        (D/'source-check.stdout').write_text(output)
        (D/'source-check.stderr').write_text('')
        receipt={
            'schema':1,'at':report['at'],'verdict':'source-and-test-preparation-complete; runtime-and-cross-evidence-pending',
            'root_contract':{'path':str(CONTRACT.relative_to(ROOT)),**identity(CONTRACT)},
            'source_observation':{'path':'verification/android-next-source-selection-2026-10-29/source-observation.json',**identity(ROOT/'verification/android-next-source-selection-2026-10-29/source-observation.json')},
            'selection_report':{'path':'verification/android-next-source-selection-2026-10-29/report.md',**identity(ROOT/'verification/android-next-source-selection-2026-10-29/report.md')},
            'accepted_input_tree':accepted['product_tree'],'derivative_product_tree':report['derivative_product_tree'],
            'derivative_source_projection':report['derivative_source_projection'],
            'product_members':16,'changed_product_files':changed,'other_fourteen_byte_identical':True,
            'host_leaves':{'members':86,'all_byte_identical_to_named_accepted_cross2_input':True,'projection':tree(host)},
            'cross_signature_leaf':cross,'descriptor':report['descriptor'],
            'expected_helpers':['NativeAppearanceViewsV2$Api29','NativeAppearanceViewsV2$Api30','NativeRenderer$Api30'],
            'emitted_helpers_observed':False,
            'tool':{**report['tool'],'executable_identity':identity(Path(sys.executable).resolve())},
            'command':report['command'],'output':{'json':identity(D/'source-check.json'),'stdout':identity(D/'source-check.stdout'),'stderr':identity(D/'source-check.stderr')},
            'source_revision_context_only':report['source_revision_context_only'],
            'operations_performed':['named source/contract reads','16 product source copies','86 mechanical leaf copies plus descriptor and JNI signature leaf','two isolated product source edits','one focused Java test source prepared','guarded Python filesystem/JSON/hash/diff/source checks'],
            'failure_preservation':'One nonexistent historical source-check.py read corrected to check_sources.py/source-verification.json; ignored local/source-inspection-correction.txt retains the error. No compiler/JVM/test startup attempted.',
            'interim_review_correction':'Mutation.requireMutation restored before pure capability preflight; focused stale/cleanup entry source controls added',
            'new_tests_executed':0,'compiler_runs':0,'native_or_capture_runs':0,
            'independent_source_design_acceptance':'pending final frozen packet review',
            'hosted_runtime_dispatch_authorized':False,'canonical_or_global_files_changed':False,
            'sdk_wire_C_JNI_descriptor_public_authority_changes':False,
            'source_pair_selection_or_lock_promotion':False,'old_BCI_or_280_subject_receipts_transfer':False,
            'prior_process_custody_native_unitA_broad_hosted_holds':'preserved; no probes, cleanup inference or equivalent v5 startup',
            'scope':'Only source/data custody passed. Prepared host tests, emitted helper bytecode, SDK37/D8 cross evidence and all native/product acceptance remain pending.'}
        (D/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        members=[]
        for path in sorted(D.rglob('*')):
            relative=path.relative_to(D)
            if relative.parts[0]=='local' or str(relative) in ('manifest.json','freeze.json') or not path.is_file():
                continue
            assert not path.is_symlink(),path
            members.append({'path':str(relative),**identity(path)})
        manifest={'schema':1,'scope':'Lean immutable source/test preparation members, excluding ignored local execution notes and this manifest/freeze','member_count':len(members),'member_bytes':sum(row['bytes'] for row in members),'members':members}
        (D/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        frozen={'schema':1,'at':report['at'],'verdict':receipt['verdict'],'derivative_product_tree':report['derivative_product_tree'],'manifest':identity(D/'manifest.json'),'member_count':len(members),'member_bytes':manifest['member_bytes'],'runtime_or_canonical_authority':False,'independent_source_design_acceptance_pending':True}
        (D/'freeze.json').write_text(json.dumps(frozen,indent=2)+'\n')
    print(output,end='')

try:
    main()
except BaseException:
    (D/'local').mkdir(exist_ok=True)
    (D/'local/source-check-failure.txt').write_text(traceback.format_exc())
    raise
