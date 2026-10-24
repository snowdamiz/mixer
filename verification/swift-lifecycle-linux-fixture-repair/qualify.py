#!/usr/bin/env python3
"""Bounded offline qualification of the immutable fixture-repair snapshot."""
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
CANDIDATE = HERE / 'candidate'
TARGET = HERE / 'owned-target'
ENV = {key: os.environ[key] for key in ['HOME', 'TMPDIR', 'USER', 'LOGNAME'] if key in os.environ}
ENV.update(PATH='/opt/homebrew/opt/rustup/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
           RUSTUP_TOOLCHAIN='stable-aarch64-apple-darwin', CARGO_TARGET_DIR=str(TARGET),
           CARGO_INCREMENTAL='0', CARGO_NET_OFFLINE='true')


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    (HERE / name).write_bytes(encoded(value))


def manifest():
    return {str(p.relative_to(CANDIDATE)): sha(p.read_bytes())
            for p in sorted(CANDIDATE.rglob('*')) if p.is_file()}


def tool_versions():
    result = {}
    for name, flags in [('rustc', ['-Vv']), ('cargo', ['-Vv']), ('rustfmt', ['--version'])]:
        proxy = shutil.which(name, path=ENV['PATH'])
        actual = subprocess.check_output(['rustup', 'which', name], env=ENV, text=True).strip()
        result[name] = {'proxy': proxy, 'proxySHA256': sha(Path(proxy).read_bytes()),
                        'actual': actual, 'actualSHA256': sha(Path(actual).read_bytes()),
                        'version': subprocess.check_output([proxy, *flags], env=ENV, text=True).strip()}
    return result


def run(label, argv):
    logs = HERE / 'commands'
    logs.mkdir(exist_ok=True)
    assert not (logs / (label + '.json')).exists(), 'preserve existing command evidence'
    prior = sum(json.loads(p.read_text())['durationSeconds'] for p in logs.glob('*.json'))
    assert prior < 900, 'aggregate command ceiling'
    bound = min(180, 900 - prior)
    before = manifest()
    assert before == json.loads((HERE / 'candidate-manifest.json').read_text())
    record = {'argv': list(map(str, argv)), 'cwd': str(CANDIDATE), 'environment': ENV,
              'startedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'timeoutSeconds': bound, 'priorCommandSeconds': prior, 'tools': tool_versions(),
              'candidateClosure': sha(encoded(before))}
    start = time.monotonic()
    child = subprocess.Popen(record['argv'], cwd=CANDIDATE, env=ENV, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    record.update(pid=child.pid, processGroup=child.pid)
    try:
        out, err = child.communicate(timeout=bound)
        record['timedOut'] = False
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGTERM)
        try:
            out, err = child.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            out, err = child.communicate()
        record['timedOut'] = True
    record.update(exitCode=child.returncode, durationSeconds=time.monotonic()-start,
                  finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  sourceUnchanged=before == manifest(), postTools=tool_versions())
    for suffix, data in [('stdout', out), ('stderr', err)]:
        (logs / (label + '.' + suffix)).write_bytes(data)
        record[suffix + 'SHA256'] = sha(data)
    processes = subprocess.check_output(['/bin/ps', '-axo', 'pid=,pgid=,command='], text=True)
    record['remainingProcessGroup'] = [line for line in processes.splitlines()
        if len(line.split(None, 2)) >= 2 and line.split(None, 2)[1] == str(child.pid)]
    save('commands/' + label + '.json', record)
    print(json.dumps({'label': label, 'exitCode': child.returncode,
                      'durationSeconds': record['durationSeconds']}), flush=True)
    assert child.returncode == 0 and not record['timedOut'] and record['sourceUnchanged'] \
        and not record['remainingProcessGroup'], label
    return out.decode()


def main():
    expected = sorted(re.findall(r'^fn (swift_lifecycle_\w+)\(',
        (CANDIDATE / 'src/experimental_swift_reactor/lifecycle_tests.rs').read_text(), re.M))
    assert len(expected) == 49
    save('test-identities.json', expected)
    helper_wrapper = HERE / 'helper-format.rs'
    helper_wrapper.write_text('#[cfg(test)]\nimpl RuntimeControl {\n' +
                              (HERE / 'test-only-helper.txt').read_text() + '}\n')
    # The existing control.rs tail and child tests have unrelated formatting debt.
    # Check all changed lifecycle source and the exact added helper independently.
    run('rustfmt-changed-scope-check', ['rustfmt', '--edition', '2021', '--config',
                                      'skip_children=true', '--check', helper_wrapper,
                                      'src/experimental_swift_reactor/lifecycle_tests.rs'])
    configs = []
    for name, flags in [('swift-debug', ['--features', 'experimental-swift-reactor']),
                        ('all-debug', ['--all-features']),
                        ('swift-release', ['--features', 'experimental-swift-reactor', '--release']),
                        ('all-release', ['--all-features', '--release'])]:
        prefix = ['cargo', 'test', '--lib', '--locked', '--offline', '--no-default-features', *flags]
        output = run(name + '-build', [*prefix, '--no-run', '--message-format=json-render-diagnostics'])
        artifacts = [json.loads(line) for line in output.splitlines() if line.startswith('{')]
        artifact = [item for item in artifacts if item.get('reason') == 'compiler-artifact'
                    and item.get('executable')][0]
        exe = Path(artifact['executable'])
        binary = exe.read_bytes()
        bindir = HERE / 'binaries'
        bindir.mkdir(exist_ok=True)
        archive = bindir / (name + '.gz')
        archive.write_bytes(gzip.compress(binary, mtime=0))
        listed_output = run(name + '-list', [exe, 'swift_lifecycle_', '--list', '--format', 'terse'])
        listed = sorted(line.removesuffix(': test') for line in listed_output.splitlines()
                        if line.endswith(': test'))
        assert sorted(item.rsplit('::', 1)[-1] for item in listed) == expected
        # Use libtest's default parallelism, as in the failing Linux CI command.
        execution = run(name + '-execute', [exe, 'swift_lifecycle_'])
        passed = sorted(re.findall(r'^test (\S+) \.\.\. ok$', execution, re.M))
        assert passed == listed and 'test result: ok. 49 passed; 0 failed; 0 ignored;' in execution
        run(name + '-production-check', ['cargo', 'check', '--lib', '--locked', '--offline',
                                        '--no-default-features', *flags])
        configs.append({'configuration': name, 'listed': listed, 'passed': passed,
                        'ignored': [], 'defaultTestParallelism': True,
                        'artifact': artifact, 'executableSHA256': sha(binary),
                        'archive': str(archive.relative_to(HERE)),
                        'archiveSHA256': sha(archive.read_bytes()),
                        'commands': [name + '-' + suffix for suffix in
                                     ['build', 'list', 'execute', 'production-check']]})
        save('configuration-results.json', configs)
    print('QUALIFIED 49 identities in 4 contexts; 196 passed; 4 production checks passed', flush=True)


if __name__ == '__main__':
    main()
