#!/usr/bin/env python3
"""Independent two-source host compile/run with bounded owned-child cleanup."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
JDK = Path('/opt/homebrew/Cellar/openjdk@25/25.0.4.1/libexec/openjdk.jdk/Contents/Home')
CANDIDATE = ROOT / 'native/android/owner-core/src/dev/mixer/android/OwnerLifecycleV2.java'
HARNESS = BASE / 'IndependentOwnerLifecycleReview.java'
EXPECTED_CANDIDATE = '4282e8284212fb042a139f597d9f34f061f6f27673e918a52f1f784e6fe9ebb6'


def digest(path):
    data = path.read_bytes()
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    label = sys.argv[1] if len(sys.argv) == 2 else 'first'
    if not label.replace('-', '').isalnum():
        raise ValueError('invalid owned attempt name')
    out = BASE / 'attempts' / label
    out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix='mixer-independent-owner-core-'))
    classes = scratch / 'classes'
    empty = scratch / 'empty'
    classes.mkdir()
    empty.mkdir()
    children = []
    commands = []
    env = dict(os.environ)
    removed_options = [key for key in ['CLASSPATH', 'JDK_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS'] if key in env]
    for key in removed_options:
        del env[key]
    env['JAVA_HOME'] = str(JDK)
    env['PATH'] = '/usr/bin:/bin'
    env['LC_ALL'] = 'C'
    completed = False
    run_summary = None
    errors = []

    def run(name, argv, timeout):
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        start = time.monotonic()
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        children.append(child)
        timed_out = False
        try:
            stdout, stderr = child.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate(timeout=15)
        elapsed = time.monotonic() - start
        (out / (name + '.stdout')).write_bytes(stdout)
        (out / (name + '.stderr')).write_bytes(stderr)
        row = {'name': name, 'argv': list(map(str, argv)), 'cwd': str(ROOT),
               'started_at': started_at, 'timeout_seconds': timeout,
               'elapsed_seconds': elapsed, 'pid': child.pid,
               'returncode': child.returncode, 'timed_out': timed_out,
               'returned_and_reaped': child.returncode is not None,
               'stdout': digest(out / (name + '.stdout')),
               'stderr': digest(out / (name + '.stderr'))}
        commands.append(row)
        write(out / 'commands.json', commands)
        if timed_out or child.returncode != 0:
            errors.append({'command': name, 'returncode': child.returncode, 'timed_out': timed_out})
        return row, stdout, stderr

    try:
        assert digest(CANDIDATE)['sha256'] == EXPECTED_CANDIDATE, 'candidate changed since producer freeze'
        snapshots = out / 'inputs'
        snapshots.mkdir()
        sources = {}
        for source in [CANDIDATE, HARNESS, Path(__file__).resolve()]:
            target = snapshots / source.name
            target.write_bytes(source.read_bytes())
            sources[str(source.relative_to(ROOT))] = digest(source)
        write(out / 'source-bindings.json', {
            'schema': 1, 'sources': sources,
            'source_tree_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
            'candidate_snapshot': str((snapshots / CANDIDATE.name).relative_to(ROOT)),
            'harness_snapshot': str((snapshots / HARNESS.name).relative_to(ROOT))})
        run('context', ['/usr/bin/git', 'rev-parse', 'HEAD'], 15)
        run('git-version', ['/usr/bin/git', '--version'], 15)
        run('javac-version', [str(JDK / 'bin/javac'), '-version'], 30)
        run('java-version', [str(JDK / 'bin/java'), '-version'], 30)
        argv = [str(JDK / 'bin/javac'), '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                '-classpath', str(empty), '-sourcepath', str(empty), '-d', str(classes),
                str(CANDIDATE), str(HARNESS)]
        compiled, _, _ = run('compile', argv, 60)
        if compiled['returncode'] == 0 and not compiled['timed_out']:
            ran, stdout, _ = run('tests', [str(JDK / 'bin/java'), '-Xmx128m', '-XX:-UsePerfData',
                '-Dfile.encoding=UTF-8', '-cp', str(classes), 'dev.mixer.android.IndependentOwnerLifecycleReview'], 60)
            for line in stdout.decode('utf-8').splitlines():
                if line.startswith('SUMMARY '):
                    run_summary = json.loads(line.removeprefix('SUMMARY '))
            completed = ran['returncode'] == 0 and not ran['timed_out'] and run_summary is not None and run_summary['failures'] == 0
        outputs = {}
        for path in sorted(classes.rglob('*.class')):
            data = path.read_bytes()
            outputs[str(path.relative_to(classes))] = {**digest(path),
                'major_version': int.from_bytes(data[6:8], 'big')}
        write(out / 'classes.json', {'schema': 1, 'count': len(outputs), 'classes': outputs})
        assert digest(CANDIDATE)['sha256'] == EXPECTED_CANDIDATE, 'candidate changed during review run'
    finally:
        cleanup_start = time.monotonic()
        for child in children:
            if child.returncode is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.communicate(timeout=15)
        all_reaped = all(child.returncode is not None for child in children)
        if all_reaped:
            shutil.rmtree(scratch)
        cleanup = {'schema': 1, 'owned_scratch': str(scratch),
            'child_pids': [child.pid for child in children],
            'all_owned_children_returned_and_reaped': all_reaped,
            'only_owned_scratch_removed_after_children_reaped': all_reaped and not scratch.exists(),
            'cleanup_seconds': time.monotonic() - cleanup_start,
            'max_child_timeout_seconds': 60, 'max_kill_reap_timeout_seconds': 15,
            'native_capture_device_or_unrelated_processes_started_or_queried': False}
        write(out / 'cleanup.json', cleanup)
        write(out / 'receipt.json', {'schema': 1,
            'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command': [sys.executable, '-B', str(Path(__file__).resolve()), label],
            'python': sys.version, 'host_platform': platform.platform(),
            'scope': 'Host ownership decisions only; no native effects, public routing, OTA, device or GA acceptance.',
            'jdk_home': str(JDK), 'removed_environment_option_names': removed_options,
            'success': completed, 'summary': run_summary, 'errors': errors,
            'cleanup': cleanup,
            'producer_tests_runner_verifier_imported_or_executed': False,
            'exact_two_compilation_sources': [str(CANDIDATE), str(HARNESS)]})
    print(json.dumps({'attempt': label, 'success': completed, 'summary': run_summary, 'errors': errors}, indent=2))
    return 0 if completed else 1


if __name__ == '__main__':
    sys.exit(main())
