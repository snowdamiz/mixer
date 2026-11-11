#!/usr/bin/env python3
"""Run public-surface and actual-renderer vertical reflow regressions on the JVM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

root = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--java-home', required=True, type=Path)
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--source-overlay', type=Path, help='Development afterimages; omitted in CI')
args = parser.parse_args()
args.evidence.mkdir(parents=True, exist_ok=False)
scratch = Path(tempfile.mkdtemp(prefix='mixer-public-surface-host-'))
commands = []
passed = False
env = os.environ.copy()
for key in ['JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH']:
    env.pop(key, None)
env['JAVA_HOME'] = str(args.java_home)
env['JAVA_TOOL_OPTIONS'] = '-XX:ActiveProcessorCount=2'
env['TMPDIR'] = str(scratch)

def run(name, argv):
    argv = list(map(str, argv))
    started = time.monotonic()
    with (args.evidence / (name + '.stdout')).open('wb') as out, (args.evidence / (name + '.stderr')).open('wb') as err:
        child = subprocess.Popen(argv, cwd=root, env=env, stdout=out, stderr=err, start_new_session=True)
        record = {'name': name, 'argv': argv, 'pid': child.pid, 'pgid': child.pid}
        commands.append(record)
        (args.evidence / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        try:
            code = child.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, 15)
            child.wait(timeout=10)
            raise
        record.update(exitCode=code, seconds=time.monotonic() - started)
        try:
            os.killpg(child.pid, 0)
            record['groupAbsent'] = False
        except ProcessLookupError:
            record['groupAbsent'] = True
        (args.evidence / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        if not record['groupAbsent'] or code != 0:
            raise RuntimeError(name + ' failed; raw evidence and scratch retained')
        print(name + ': PASS', flush=True)

try:
    tests = root / 'native/android/tests'
    roster = json.loads((tests / 'private-owner-host-roster.json').read_text())['closures']['A-orchestration']
    sources = {Path(f).name: root / f for f in roster['actual_production_sources']}
    sources['AndroidUINativeSurface.java'] = root / 'native/android/app/src/dev/mixer/android/AndroidUINativeSurface.java'
    if args.source_overlay:
        for row in json.loads(args.source_overlay.read_text()):
            f = Path(row['source'])
            if f.name not in sources or hashlib.sha256(f.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('source overlay mismatch')
            sources[f.name] = f
    leaves = sorted((tests / 'NativeOwnerV2HostLeaves').rglob('*.java'))
    suites = [('observer-settlement', 'dev.mixer.android.DeadObserverControl', 'DeadObserverControl.java'),
              ('focus-admission', 'dev.mixer.android.OwnerRefreshAdmissionHostTests', 'OwnerRefreshAdmissionHostTests.java'),
              ('public-consumer', 'example.customer.PublicSurfaceConsumerTest', 'PublicSurfaceConsumerTest.java'),
              ('external-source', 'dev.mixer.android.ExternalFrameSourceV2HostTests', 'ExternalFrameSourceV2HostTests.java')]
    inputs = sorted(set(sources.values()) | set(leaves) | {tests / f for _, _, f in suites})
    (args.evidence / 'inputs.json').write_text(json.dumps({str(f.relative_to(root)) if f.is_relative_to(root) else str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}, indent=2) + '\n')
    classes = scratch / 'classes'
    classes.mkdir()
    run('compile', [args.java_home / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '', '-classpath', '', '-d', classes, *inputs])
    descriptor = root / 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
    for name, main, _ in suites:
        run(name, [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', classes, main, descriptor])
    # Same production source closure and controlled leaves as the accepted R58 test.
    concrete = json.loads((tests / 'private-owner-host-roster.json').read_text())['closures']['B-concrete-renderer-views']
    concrete_sources = {Path(f).name: root / f for f in concrete['actual_production_sources']}
    if args.source_overlay:
        for row in json.loads(args.source_overlay.read_text()):
            f = Path(row['source'])
            if f.name in concrete_sources:
                concrete_sources[f.name] = f
    concrete_leaves = sorted((tests / 'NativeOwnerV2ConcreteHostLeaves').rglob('*.java'))
    reflow_inputs = sorted(set(concrete_sources.values()) | set(concrete_leaves) | {tests / 'VerticalReflowHostTests.java', tests / 'GeneratedAddTransitionHostTests.java', tests / 'FocusedDisableOwnerTransitionHostTests.java', tests / 'CompleteHandoffHostTests.java', tests / 'FailureDismissalHostTests.java', tests / 'CapturedPredecessorCustodyHostTests.java', tests / 'EditorTransactionHostTests.java', tests / 'EditorOpacityHostTests.java', tests / 'MeasuredAcknowledgmentHostTests.java', tests / 'MeasuredAcknowledgmentPreservationHostTests.java', tests / 'ContainerFrameWitnessHostTests.java'})
    (args.evidence / 'vertical-reflow-inputs.json').write_text(json.dumps({str(f.relative_to(root)) if f.is_relative_to(root) else str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in reflow_inputs}, indent=2) + '\n')
    reflow_classes = scratch / 'vertical-reflow-classes'
    reflow_classes.mkdir()
    run('vertical-reflow-compile', [args.java_home / 'bin/javac', '--release', '17', '-Xlint:all', '-Werror', '-proc:none', '-sourcepath', '', '-classpath', '', '-d', reflow_classes, *reflow_inputs])
    run('vertical-reflow', [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.VerticalReflowHostTests', descriptor, 'candidate'])
    packets = tests / 'GeneratedAddTransitionPackets'
    packet_inputs = [packets / name for name in ('opened.packet.json', 'typed.packet.json', 'added.packet.json', 'descriptor.json')]
    (args.evidence / 'generated-add-packet-inputs.json').write_text(json.dumps({str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in packet_inputs}, indent=2) + '\n')
    run('generated-add-transition', [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.GeneratedAddTransitionHostTests', packets, 'candidate'])
    focused_packets = tests / 'FocusedDisableOwnerTransitionPackets'
    focused_inputs = [focused_packets / name for name in ('descriptor.json', 'synthesized-acknowledged-presave.json', '201-2.json', '201-3.json')]
    (args.evidence / 'focused-disable-packet-inputs.json').write_text(json.dumps({str(f.relative_to(root)): hashlib.sha256(f.read_bytes()).hexdigest() for f in focused_inputs}, indent=2) + '\n')
    run('focused-disable-transition', [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.FocusedDisableOwnerTransitionHostTests', focused_packets, 'candidate'])
    editor_packets = tests / 'EditorTransactionPackets'
    editor_pins = json.loads((editor_packets / 'inputs.json').read_bytes())
    for name, expected in editor_pins.items():
        raw = (editor_packets / name).read_bytes()
        if {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} != expected:
            raise ValueError('editor packet identity differs: ' + name)
    (args.evidence / 'editor-transaction-packet-inputs.json').write_text(json.dumps(editor_pins, indent=2) + '\n')
    for main in ('CompleteHandoffHostTests', 'FailureDismissalHostTests', 'CapturedPredecessorCustodyHostTests', 'EditorTransactionHostTests'):
        run(main, [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.' + main, editor_packets])
    for main in ('MeasuredAcknowledgmentHostTests', 'MeasuredAcknowledgmentPreservationHostTests', 'ContainerFrameWitnessHostTests'):
        run(main, [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.' + main, editor_packets, 'candidate', focused_packets])
    run('editor-opacity', [args.java_home / 'bin/java', '-ea', '-Xmx256m', '-cp', reflow_classes, 'dev.mixer.android.EditorOpacityHostTests', editor_packets / 'descriptor.json', editor_packets / 'before-public-reset/00.json'])
    passed = True
finally:
    if passed:
        shutil.rmtree(scratch)
    (args.evidence / 'result.json').write_text(json.dumps({'passed': passed, 'scope': 'JVM public suites with controlled renderer; vertical reflow, production-packet Add/clear and focused model-disable with actual renderer/owner/views and controlled Android/JNI leaves; no device qualification', 'scratch': str(scratch), 'scratchRemoved': passed, 'commands': len(commands)}, indent=2) + '\n')
