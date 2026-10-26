#!/usr/bin/env python3
"""Compile actual Observer plus a frozen, explicit independently authored leaf list."""
import argparse
import datetime
import sys
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import time

REPOSITORY = Path(__file__).resolve().parents[3]
BASE = 'native/android/tests/NativeEnvironmentV2ObserverHostLeaves/'
LEAVES = (
    'android/app/Activity.java', 'android/app/UiModeManager.java',
    'android/content/ComponentCallbacks.java', 'android/content/ContentResolver.java',
    'android/content/Context.java', 'android/content/res/Configuration.java',
    'android/content/res/Resources.java', 'android/database/ContentObserver.java',
    'android/graphics/Insets.java', 'android/net/Uri.java', 'android/os/Build.java',
    'android/os/Handler.java', 'android/os/LocaleList.java', 'android/os/Looper.java',
    'android/provider/Settings.java', 'android/util/DisplayMetrics.java',
    'android/util/TypedValue.java', 'android/view/View.java', 'android/view/ViewTreeObserver.java',
    'android/view/Window.java', 'android/view/WindowInsets.java',
    'android/view/accessibility/AccessibilityManager.java', 'android/widget/FrameLayout.java',
    'dev/mixer/android/AppearanceDescriptorV2.java', 'dev/mixer/android/AppearanceGeometryV2.java',
    'dev/mixer/android/AppearanceResolverV2.java', 'dev/mixer/android/NativeRenderer.java',
    'dev/mixer/android/ObserverHostProbe.java',
)
SOURCES = ('native/android/app/src/dev/mixer/android/NativeEnvironmentV2.java',
           'native/android/tests/NativeEnvironmentV2ObserverHostTests.java') + tuple(BASE + p for p in LEAVES)
SELF = 'native/android/tests/run-environment-observer-host.py'
MANIFEST = REPOSITORY / 'verification/android-environment-observer-lifecycle/host-source-freeze.json'
STRIP = ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS')

def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--jdk', type=Path, default=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=False)
    expected = set(SOURCES + (SELF,))
    snapshots = {relative: (REPOSITORY/relative).read_bytes() for relative in sorted(expected)}
    freeze = {'context_revision': subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPOSITORY,text=True).strip(),
              'files': {relative:identity(data) for relative,data in snapshots.items()}}
    save(evidence/'source-freeze.json',freeze)
    for relative, data in snapshots.items():
        target=evidence/'inputs'/relative
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
    env = dict(os.environ)
    stripped = {name: name in env for name in STRIP}
    for name in STRIP:
        env.pop(name, None)
    scratch = Path(tempfile.mkdtemp(prefix='observer-owned-', dir=evidence))
    commands = []
    def run(label, argv, timeout=45):
        start = time.time()
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   env=env, cwd=REPOSITORY, start_new_session=True)
        timed_out = False
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate()
        (evidence / (label + '.stdout')).write_bytes(out)
        (evidence / (label + '.stderr')).write_bytes(err)
        entry = {'label': label, 'argv': [str(p) for p in argv], 'exit': process.returncode,
                 'timed_out': timed_out, 'child_reaped': True, 'elapsed_seconds': time.time()-start,
                 'stdout': identity(out), 'stderr': identity(err)}
        commands.append(entry)
        save(evidence/'commands.json', commands)
        if timed_out or process.returncode:
            raise RuntimeError(label + ' failed; retained streams: ' + str(evidence))
        return out
    status = 'failed'
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'argv': [sys.executable, *sys.argv], 'python_version': sys.version, 'scope': 'Java17 host execution of actual Observer with faulting Android/renderer leaves; no native behavior',
               'source_freeze': identity((evidence/'source-freeze.json').read_bytes()), 'source_revision': freeze['context_revision'],
               'environment': {'platform': os.uname().sysname, 'machine': os.uname().machine,
                               'stripped_implicit_jvm_variables': stripped}, 'native_or_capture_processes_started_or_queried': False,
               'new_dependencies': [], 'commands': 'commands.json'}
    try:
        java_home = args.jdk.resolve(strict=True)
        javac, java = java_home/'bin/javac', java_home/'bin/java'
        receipt['tools'] = {str(p): identity(p.resolve().read_bytes()) for p in (javac,java)}
        run('javac-version', [str(javac), '-version'])
        run('java-version', [str(java), '-version'])
        run('revision', ['git', 'rev-parse', 'HEAD'])
        files = []
        for relative in SOURCES:
            target = scratch/'source'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(snapshots[relative]); files.append(str(target))
        classes, empty = scratch/'classes', scratch/'empty'
        classes.mkdir(); empty.mkdir()
        run('compile', [str(javac), '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                        '-classpath', str(empty), '-sourcepath', str(empty), '-d', str(classes)] + files)
        receipt['classes'] = {str(p.relative_to(classes)):identity(p.read_bytes()) for p in sorted(classes.rglob('*.class'))}
        result = run('host', [str(java), '-ea', '-Xmx128m', '-cp', str(classes),
                             'dev.mixer.android.NativeEnvironmentV2ObserverHostTests'], timeout=30)
        if not result.startswith(b'PASS '):
            raise RuntimeError('missing explicit host success')
        status='passed-host-only'
        print(result.decode().strip())
    except BaseException as failure:
        receipt['failure'] = {'type': type(failure).__name__, 'message': str(failure)}
        raise
    finally:
        shutil.rmtree(scratch)
        receipt.update(status=status, cleanup={'owned_scratch_removed': not scratch.exists(),
            'owned_children_reaped': all(c['child_reaped'] for c in commands),
            'native_or_capture_instances_created': False},
            pending=['Native Android runtime and final phones', 'Public V2 integration', 'GA qualification'])
        save(evidence/'receipt.json',receipt)

if __name__ == '__main__':
    main()
