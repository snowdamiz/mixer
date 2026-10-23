#!/usr/bin/env python3
"""Check retained source/log/executable bindings for this bounded CI repair."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPAIR = ROOT / 'verification/android-fault-leave-ci-repair'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def require(c, message):
    if not c:
        raise RuntimeError(message)

def main():
    checks = []
    bindings = {}
    replays = []
    def bind(path, expected):
        require(sha(path) == expected, 'SHA mismatch: ' + str(path))
        bindings[str(path.relative_to(ROOT))] = expected
    rel = 'verification/android-binding-stage4/HostTests.swift'
    failed_path = REPAIR / 'failed-hosted-artifact/android-binding-tsan/receipt.json'
    failed = json.loads(failed_path.read_text())
    bindings[str(failed_path.relative_to(ROOT))] = sha(failed_path)
    old = REPAIR / 'original-HostTests.swift'
    bind(old, failed['input_files'][rel])
    require(subprocess.check_output(['git', 'show', failed['revision'] + ':' + rel], cwd=ROOT) == old.read_bytes(),
            'Original does not match failed hosted revision')
    failure = [c for c in failed['commands'] if c['name'] == 'fault-leave']
    require(len(failure) == 1 and failure[0]['exit'] == -5, 'Wrong hosted failure')
    failed_log = failed_path.parent / 'logs/fault-leave.log'
    bind(failed_log, failure[0]['sha256'])
    require('HOST_FAIL line=109 test observation deadline' in failed_log.read_text(), 'Failure diagnostic differs')
    checks.append('Failed hosted c687e69 receipt binds original fixture and exact sparse -5 deadline log')
    expected = old.read_text().replace(
        'private func waitUntil(_ predicate: () -> Bool) async throws {',
        'private func waitUntil(line: Int = #line, _ predicate: () -> Bool) async throws {').replace(
        '        require(ContinuousClock.now < deadline, "test observation deadline")',
        '        require(ContinuousClock.now < deadline, "test observation deadline", line: line)').replace(
        '        try await waitUntil { transport().completions > 0 }\n'
        '        let xc = try frameExchange(902); let ic = try await c.binding.bindHost(xc)\n'
        '        require(mxish_wait_hold() == 0, "actual C active entry")\n',
        '        // A completion count can be observed inside b\'s callback, before its\n'
        '        // leave hint is consumed. If c joins that same callback, its leave\n'
        '        // coalesces with b\'s pending byte and never attempts the injected write.\n'
        '        // Observe b\'s entire callback/fence delivery before admitting c.\n'
        '        try await waitUntil {\n'
        '            let snapshot = transport()\n'
        '            return snapshot.completions > 0 && snapshot.pending_pipe_hint == 0 && snapshot.callback_active == 0\n'
        '        }\n'
        '        let xc = try frameExchange(902); let ic = try await c.binding.bindHost(xc)\n'
        '        require(mxish_wait_hold() == 0, "actual C active entry")\n'
        '        require(transport().pending_pipe_hint == 0, "held c leave must attempt a fresh write")\n')
    require((ROOT / rel).read_text() == expected, 'Candidate contains extra or missing fixture changes')
    checks.append('Candidate is exactly caller-line diagnostics plus idle wait plus fresh-write assertion; original fanout/stop assertions unchanged')
    cases = None
    for mode in ['debug', 'release', 'tsan']:
        path = REPAIR / (mode + '-receipt.json')
        r = json.loads(path.read_text())
        bindings[str(path.relative_to(ROOT))] = sha(path)
        require(r['status'] == 'passed' and len(r['cases_executed']) == 39, 'Incomplete ordinary runner ' + mode)
        require(cases is None or cases == r['cases_executed'], 'Different scenario set')
        cases = r['cases_executed']
        require(set(failed['input_files']) == set(r['input_files']), 'Input set changed')
        changed = [p for p in r['input_files'] if r['input_files'][p] != failed['input_files'][p]]
        require(changed == [rel], 'Production source changed from failing hosted inputs')
        for relative, digest in r['input_files'].items():
            bind(ROOT / relative, digest)
        snapshot = ROOT / 'verification/android-fault-leave-ci-repair/build' / ('fresh-' + mode) / 'source'
        for relative, digest in r['source_files'].items():
            bind(snapshot / relative, digest)
        require(hashlib.sha256(json.dumps(r['source_files'], sort_keys=True).encode()).hexdigest() == r['source_tree_sha256'],
                'Wrong source tree digest')
        for c in r['commands']:
            require(c['exit'] == 0, 'Failed local command')
            log = REPAIR / (mode + '-logs') / Path(c['log']).name
            bind(log, c['sha256'])
            require('WARNING: ThreadSanitizer' not in log.read_text(errors='replace'), 'TSan warning')
        for scenario in r['cases_executed']:
            require('HOST_PASS ' + scenario in (REPAIR / (mode + '-logs') / (scenario + '.log')).read_text().splitlines(),
                    'Ordinary exact success marker absent')
        build_command = [c for c in r['commands'] if c['name'] == 'fresh-build']
        require(len(build_command) == 1 and ('--sanitize' in build_command[0]['argv']) == (mode == 'tsan'),
                'Wrong sanitizer build mode')
        bind(Path(r['executable']['path']), r['executable']['sha256'])
        argv = [r['executable']['path'], 'fault-leave']
        replay = subprocess.run(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
        replay_log = HERE / (mode + '-original-fixture-replay.log')
        replay_log.write_bytes(replay.stdout)
        require(replay.returncode == 0 and b'HOST_PASS fault-leave' in replay.stdout.splitlines() and
                b'WARNING: ThreadSanitizer' not in replay.stdout, 'Independent original fixture replay failed: ' + mode)
        bind(replay_log, sha(replay_log))
        replays.append({'mode': mode, 'argv': argv, 'cwd': str(ROOT), 'exit': replay.returncode,
                       'log': str(replay_log.relative_to(ROOT)), 'sha256': sha(replay_log)})
        for relative, digest in r['native_inputs'].items():
            bind(Path(relative), digest)
        bind(Path(r['native_receipt']), r['native_receipt_sha256'])
        checks.append(mode + ': 39 exact ordinary markers, source snapshot, executable, native inputs and every command log bound; 150/151 inputs unchanged from failing hosted build')
    checks.append('Independent unmodified candidate fault-leave executable replay passes once each Debug/Release/TSan')
    schedule_path = REPAIR / 'schedule-receipt.json'
    schedule = json.loads(schedule_path.read_text())
    bindings[str(schedule_path.relative_to(ROOT))] = sha(schedule_path)
    for relative, digest in schedule['inputs'].items():
        bind(ROOT / relative, digest)
    for c in schedule['commands']:
        require(c['exit'] == 0, 'C schedule failed')
        bind(ROOT / c['log'], c['sha256'])
    checks.append('Root C schedule retained inputs/commands/logs verified; mechanism only, not exact hosted cause')
    probe_path = HERE / 'probe-receipt.json'
    probe = json.loads(probe_path.read_text())
    require(probe['status'] == 'passed', 'Independent Swift/C probe incomplete')
    bindings[str(probe_path.relative_to(ROOT))] = sha(probe_path)
    for c in probe['commands']:
        require(c['exit'] == 0, 'Independent probe command failed')
        bind(ROOT / c['log'], c['sha256'])
    for relative, digest in probe['copied_source_files'].items():
        bind(HERE / 'build/task-barrier/source' / relative, digest)
    for name, digest in probe['review_inputs'].items():
        bind(HERE / name, digest)
    for exe in probe['executables'].values():
        bind(Path(exe['path']), exe['sha256'])
    checks.append('Independent actual Swift/C old/fixed schedules pass Debug/Release/TSan; delayed b task parks after fixed idle without further native request')
    out = {'observed_utc': datetime.now(timezone.utc).isoformat(),
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'command': [sys.executable, str(Path(__file__))], 'cwd': str(ROOT),
        'python_version': sys.version, 'git_version': subprocess.check_output(['git', '--version'], text=True).strip(),
        'audit_sha256': sha(Path(__file__)), 'checks': checks, 'independent_original_fixture_replays': replays, 'bindings': bindings,
        'binding_count': len(bindings), 'status': 'passed',
        'findings': [], 'scope': 'Bounded test-only Android fault-leave CI repair independent review; no whole-product or device/GA qualification. Exact hosted scheduling cause remains unproved.'}
    (HERE / 'audit-receipt.json').write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps({'status': out['status'], 'checks': checks, 'binding_count': len(bindings)}, indent=2))

if __name__ == '__main__':
    main()
