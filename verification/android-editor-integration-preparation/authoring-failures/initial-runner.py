#!/usr/bin/env python3
"""Prospective integration check of unchanged A/B suites against frozen candidate.

This owns only this evidence directory. It does not promote candidate sources.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
CANDIDATE = ROOT / 'verification/android-editor-replacement-implementation'
SEAL = '4c906824fe5e2e925c3ad5ca7c4ae94ba3b1e7dd6c58e77805dd3862c165c9a3'
JDK = Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')


def ident(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--closure', choices=('A', 'B'), required=True)
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    if not args.run.isalnum():
        raise ValueError('run must be an alphanumeric local name')
    out = D / ('closure-' + args.closure + '-' + args.run)
    out.mkdir(exist_ok=False)
    seal_bytes = (CANDIDATE / 'seal.json').read_bytes()
    assert ident(seal_bytes)['sha256'] == SEAL
    sealed = {v['path']: v for v in json.loads(seal_bytes)['files']}
    roster_path = ROOT / 'verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
    roster = json.loads(roster_path.read_bytes())['closures'][
        'A-orchestration' if args.closure == 'A' else 'B-concrete-renderer-views']
    sources = {}
    origins = {}

    def add(key, path, replacement=None):
        data = path.read_bytes()
        origin = {'source': str(path.relative_to(ROOT)), **ident(data)}
        if path.is_relative_to(CANDIDATE):
            row = sealed[str(path.relative_to(CANDIDATE))]
            assert ident(data) == {'bytes': row['bytes'], 'sha256': row['sha256']}
        if replacement is not None:
            before, after = replacement
            assert data.count(before) == 1
            data = data.replace(before, after)
            origin['controlled_leaf_adaptation'] = 'Add scalar editorDisposalBusyV2 false to existing orchestration-only renderer leaf; no editor behavior modeled'
        assert key not in sources
        sources[key] = data
        origins[key] = origin

    if args.closure == 'A':
        for source in roster['actual_production_sources'] + ['native/android/app/src/dev/mixer/android/NativeEnvironmentPlatformV2.java']:
            add('product/' + Path(source).name, CANDIDATE / 'source' / Path(source).name)
        for row in roster['substitutes']:
            path = ROOT / row['source']
            replacement = None
            if row['fqcn'] == 'dev.mixer.android.NativeRenderer':
                replacement = (b' boolean cancellationInProgressV2()', b' boolean editorDisposalBusyV2(){return false;}\n boolean cancellationInProgressV2()')
            add('leaves/' + row['fqcn'].replace('.', '/') + '.java', path, replacement)
    else:
        for path in sorted((CANDIDATE / 'source').glob('*.java')):
            add('product/' + path.name, path)
        for path in sorted((CANDIDATE / 'host-leaves').rglob('*.java')):
            add('leaves/' + str(path.relative_to(CANDIDATE / 'host-leaves')), path)
    # B candidate leaves already contain its unchanged ConcreteHostProbe.
    for source in roster['test_support_sources']:
        if args.closure == 'A':
            add('support/' + Path(source).name, ROOT / source)
        else:
            counterpart = CANDIDATE / 'host-leaves/dev/mixer/android' / Path(source).name
            assert counterpart.read_bytes() == (ROOT / source).read_bytes()
    add('tests/' + Path(roster['test_source']).name, ROOT / roster['test_source'])
    for key, path in [('descriptor.json', ROOT / 'verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'),
                      ('barrier-map.json', ROOT / 'verification/android-private-owner-integration-implementation/barrier-map.json'),
                      ('roster.json', roster_path), ('runner.py', Path(__file__))]:
        add('auxiliary/' + key, path)
    for name, data in sources.items():
        path = out / 'inputs' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    save(out / 'source-map.json', {name: ident(data) for name, data in sources.items()})
    save(out / 'source-origins.json', origins)
    commands = []
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'scope': 'Existing unchanged owner host closure with exact frozen candidate products and explicitly adapted controlled leaves; not independent editor acceptance',
               'candidate_seal_sha256': SEAL, 'closure': args.closure,
               'argv': sys.argv, 'python': sys.version, 'status': 'failed',
               'canonical_or_native_or_GA_accepted': False}
    scratch = Path(tempfile.mkdtemp(prefix='owned-existing-closure-', dir=out))
    env = dict(os.environ)
    for name in ('_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', 'CLASSPATH', 'JAVA_OPTS', 'JDK_JAVAC_OPTIONS'):
        env.pop(name, None)
    temp = scratch / 'tmp'
    temp.mkdir()
    for name in ('TMPDIR', 'TMP', 'TEMP'):
        env[name] = str(temp)

    def run(label, argv, deadline=60):
        stdout, stderr = out / (label + '.stdout'), out / (label + '.stderr')
        start = time.monotonic()
        timed = overflow = False
        with stdout.open('wb') as sout, stderr.open('wb') as serr:
            child = subprocess.Popen([str(a) for a in argv], cwd=out, env=env,
                                     stdout=sout, stderr=serr, start_new_session=True)
            try:
                while child.poll() is None:
                    timed = time.monotonic() - start >= deadline
                    overflow = max(stdout.stat().st_size, stderr.stat().st_size) > 8_000_000
                    if timed or overflow:
                        os.killpg(child.pid, signal.SIGKILL)
                        break
                    time.sleep(.05)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        row = {'label': label, 'argv': [str(a) for a in argv], 'exit': child.returncode,
               'seconds': time.monotonic() - start, 'deadline_seconds': deadline,
               'timeout': timed, 'overflow': overflow, 'child_reaped': True,
               'stdout': ident(stdout.read_bytes()), 'stderr': ident(stderr.read_bytes())}
        commands.append(row)
        save(out / 'commands.json', commands)
        if timed or overflow or child.returncode:
            raise RuntimeError(label + ' failed; retained exact outputs')
        return stdout.read_bytes()

    try:
        java, javac = JDK / 'bin/java', JDK / 'bin/javac'
        receipt['tools'] = {str(p): ident(p.resolve().read_bytes()) for p in (java, javac)}
        run('java-version', [java, '-version'])
        run('javac-version', [javac, '-version'])
        empty, classes = scratch / 'empty', scratch / 'classes'
        empty.mkdir()
        classes.mkdir()
        files = [out / 'inputs' / name for name in sources if name.endswith('.java')]
        run('compile', [javac, '--release', '17', '-Xlint:all', '-Werror', '-proc:none',
                        '-classpath', empty, '-sourcepath', empty, '-d', classes, *files])
        shutil.copytree(classes, out / 'classes')
        save(out / 'class-map.json', {str(p.relative_to(classes)): ident(p.read_bytes()) for p in sorted(classes.rglob('*.class'))})
        result = run('host', [java, '-ea', '-Xmx256m', '-cp', classes,
                             'dev.mixer.android.NativeOwnerV2' + ('Concrete' if args.closure == 'B' else '') + 'HostTests',
                             out / 'inputs/auxiliary/descriptor.json', out / 'observed-sites.txt',
                             out / 'inputs/auxiliary/barrier-map.json', out / 'barrier-cases.json'], 300)
        assert result.startswith(b'PASS '), 'missing complete host PASS'
        receipt['status'] = 'passed-prospective-integration-host-only'
        print(result.decode().strip())
    except BaseException as exc:
        receipt['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        raise
    finally:
        shutil.rmtree(scratch)
        receipt['cleanup'] = {'scratch_removed': not scratch.exists(), 'owned_children_reaped': all(c['child_reaped'] for c in commands),
                              'native_or_capture_processes_started_or_queried': False}
        receipt['candidate_seal_stable'] = (CANDIDATE / 'seal.json').read_bytes() == seal_bytes
        receipt['frozen_inputs_stable'] = all((out / 'inputs' / n).read_bytes() == b for n, b in sources.items())
        save(out / 'receipt.json', receipt)


if __name__ == '__main__':
    main()
