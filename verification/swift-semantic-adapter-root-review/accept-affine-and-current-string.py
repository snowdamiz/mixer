"""Write-once bounded root decisions, after direct source and review inspection."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SHA = lambda b: hashlib.sha256(b).hexdigest()
KINDS = {
    'affine': {
        'packets': [
            ('swift-guarded-snapshot-prepaid-input-owner-affine-refusal', '2270f59809b80c49df907a7ea9c20faf4dd45735cabad275ae61065efc19c50b', 67, 1728034),
            ('swift-guarded-snapshot-prepaid-affine-refusal-independent', '25eb5a5f02059ab38953f9435bef2e308e2e946290c231ebd922459e20dd679d', 35, 1261305),
        ],
        'checker': 'seal_review.py',
        'acceptance': 'guarded-snapshot-prepaid-affine-refusal-host-acceptance.json',
    },
    'string': {
        'packets': [
            ('swift-guarded-snapshot-string-provider-source-rebind', '3782b36c05e5ef0d4037cdac26834b31f3db1978250ba25abd2a869e4c5b90ab', 657, 128097360),
            ('swift-guarded-snapshot-string-provider-rebind-independent', '7048717734e68adc9ee56be046217232818322b4baad0dabb978444e02c229af', 262, 64153311),
        ],
        'checker': 'seal.py',
        'acceptance': 'guarded-snapshot-string-provider-source-rebind-host-acceptance.json',
    },
}


def row(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': SHA(data)}


def save(path, data):
    with path.open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def custody(spec):
    result = []
    for name, digest, count, total in spec['packets']:
        base = ROOT / 'verification' / name
        assert row(base / 'seal.json')['sha256'] == digest
        seal = json.loads((base / 'seal.json').read_bytes())
        members = seal['members']
        names = [m['path'] for m in members]
        assert len(set(names)) == len(names) == count == seal['member_count']
        assert sum(m['bytes'] for m in members) == total == seal['member_bytes']
        assert all(not p.is_symlink() for p in base.rglob('*'))
        assert {str(p.relative_to(base)) for p in base.rglob('*') if p.is_file()} == set(names) | {'seal.json'}
        for m in members:
            rel = Path(m['path'])
            assert not rel.is_absolute() and '..' not in rel.parts
            p = base / rel
            data = p.read_bytes()
            assert len(data) == m['bytes'] and SHA(data) == m['sha256'], p
            assert not stat.S_IMODE(p.stat().st_mode) & 0o222, p
        result.append({'path': str(base.relative_to(ROOT)), 'seal_sha256': digest, 'members': count, 'bytes': total})
    return result


def exists(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def main():
    kind = sys.argv[1]
    spec = KINDS[kind]
    out = HERE / (kind + '-source-review-root-check')
    accept = HERE / spec['acceptance']
    assert not out.exists() and not accept.exists(), 'one-shot root decision'
    out.mkdir()
    before = custody(spec)
    review = ROOT / 'verification' / spec['packets'][1][0]
    env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0'}
    argv = [sys.executable, '-B', str(review / spec['checker']), '--check']
    plan = {'argv': argv, 'cwd': str(ROOT), 'environment': env, 'timeout_seconds': 45,
            'termination_grace_seconds': [5, 5], 'python_version': sys.version,
            'python_executable_sha256': SHA(Path(sys.executable).resolve().read_bytes()),
            'root_script': row(Path(__file__).resolve()), 'checker': row(review / spec['checker']),
            'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, timeout=10, text=True).strip(),
            'custody_before': before, 'scope': 'read-only frozen custody, no compiler or test replay'}
    save(out / 'plan.json', plan)
    start = time.monotonic()
    child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    timed = False
    signals = []
    try:
        stdout, stderr = child.communicate(timeout=45)
    except subprocess.TimeoutExpired:
        timed = True
        if exists(child.pid):
            os.killpg(child.pid, signal.SIGTERM)
            signals.append('SIGTERM')
        try:
            stdout, stderr = child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if exists(child.pid):
                os.killpg(child.pid, signal.SIGKILL)
                signals.append('SIGKILL')
            stdout, stderr = child.communicate(timeout=5)
    for name, data in [('stdout', stdout), ('stderr', stderr)]:
        with (out / name).open('xb') as stream:
            stream.write(data)
    receipt = {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
               'elapsed_seconds': time.monotonic() - start, 'owned_pid': child.pid, 'owned_pgid': child.pid,
               'child_reaped': child.returncode is not None, 'owned_group_absent': not exists(child.pid),
               'cleanup_signals': signals, 'outputs': [row(out / n) for n in ['stdout', 'stderr']],
               'plan': row(out / 'plan.json'), 'at': datetime.now(timezone.utc).isoformat()}
    save(out / 'receipt.json', receipt)
    assert child.returncode == 0 and not timed and receipt['owned_group_absent']
    assert custody(spec) == before
    check = json.loads(stdout)
    assert check['seal_sha256'] == spec['packets'][1][1]
    assert check['members'] == spec['packets'][1][2]
    decision = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
                'custody': before, 'root_check_receipt': row(out / 'receipt.json'),
                'direct_root_inspection': 'candidate ownership/refusal/retirement and typed schema; current-source caller/constant/compiler binding and independent controls',
                'all_frozen_members_unchanged': True, 'prior_failures_preserved': True,
                'root_policy_or_native_prices_selected': False, 'root_funding_selected': False,
                'actual_Rust_acquisition_or_authenticated_owner_accepted': False,
                'current_whole_host_L_str_selected': False, 'actual_successful_loader_writer_execution': False,
                'native_runtime_or_FieldLog_or_OTA_or_GA_accepted': False,
                'new_compiler_product_native_UI_capture_invocations': 0}
    if kind == 'affine':
        report_path = review / 'report.json'
        report = json.loads(report_path.read_bytes())
        assert report['findings'] == [] and report['blocking_findings'] == 0
        assert report['independence']['fresh_methods'] == 35 and report['independence']['fresh_failures'] == 0
        assert report['fresh_contract_controls']['exhaustive_successful_read_schedules_small_extents'] == 58904
        assert report['preserved_limits']['policy_fields'] == 17
        assert report['preserved_limits']['all3_selectors'] == report['preserved_limits']['all6_upstream_needs'] == 'Pending'
        final = review / 'commands/complete-final'
        command = json.loads((final / 'receipt.json').read_bytes())
        assert command['exit'] == 0 and not command['timed_out']
        assert command['child_reaped'] and command['owned_group_absent'] and command['inputs_unchanged']
        assert b'Ran 35 tests' in (final / 'stderr').read_bytes() and b'\nOK\n' in (final / 'stderr').read_bytes()
        for entry in command['outputs']:
            assert row(ROOT / entry['path']) == entry
        for entry in command['source_after']:
            assert row(ROOT / entry['path']) == entry
        decision.update({'status': 'root-accepted-bounded-synthetic-trusted-local-affine-refusal-and-strict-session-model',
            'independent_report': row(report_path), 'fresh_methods': 35, 'fresh_read_schedules': 58904,
            'C1': report['C1'], 'C2': report['C2'], 'controls': report['fresh_contract_controls'],
            'preserved_limits': report['preserved_limits'],
            'mandatory_boundary': ['12 synthetic ingress units are not native prices',
                'consume first attempt and retain safe fixed roster before fallible checks',
                'unsafe foreign oversized or unknown obligations retain whole charge',
                'finite replay slot does not pay for unbounded external caller work',
                'all thirteen original owners plus distinct loader owners remain funded through actual retirement',
                'synthetic identity parser is not authenticated manifest or native owner proof'],
            'actual_Rust_implementation_remains_required': True})
    else:
        report_path = review / 'analysis.json'
        report = json.loads(report_path.read_bytes())
        assert report['blocking_candidate_findings'] == []
        assert report['current_source_tree'] == 'acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d'
        assert report['fresh_controls'] == {'caller': 10, 'census': 7, 'typed_groups': 8, 'typed_individual_controls': 1122}
        assert len(report['qualifying_commands']) == 12
        for selected in report['qualifying_commands']:
            command_path = review / selected['receipt']
            command = json.loads(command_path.read_bytes())
            assert command['success'] and command['exit_code'] == 0 and not command['timed_out']
            assert command['child_reaped'] and command['owned_group_absent'] and command['input_custody_unchanged']
            for entry in command['outputs']:
                data = (command_path.parent / entry['path']).read_bytes()
                assert len(data) == entry['bytes'] and SHA(data) == entry['sha256']
            for entry in command['scripts']:
                data = (review / entry['path']).read_bytes()
                assert len(data) == entry['bytes'] and SHA(data) == entry['sha256']
        assert not any(report[k] for k in ['GA', 'L_str_selected', 'OTA', 'actual_current_success_path_qualified',
            'actual_future_caller_selected', 'current_metadata_query_is_final_fixture_executable', 'whole_host_funding_selected'])
        decision.update({'status': 'root-accepted-bounded-conditional-current-provider-source-MIR-string-rebind',
            'independent_report': row(report_path), 'source_tree': report['current_source_tree'],
            'host11_tree': report['current_host11_tree'], 'fresh_controls': report['fresh_controls'],
            'qualifying_commands': report['qualifying_commands'], 'typed_summary': report['typed_summary'],
            'limitations': report['limitations'], 'conditional_envelope_bytes': 5080,
            'COMPILED_five_None_is_substantive_UnsupportedBuild': True,
            'potential_success_obligations_preserved': True,
            'future_injected_identity_requires_fresh_source_constant_census_compiler_build_session_executable_binding': True,
            'producer_historical_failures': 9, 'reviewer_historical_failures': 3})
    save(accept, decision)
    print(json.dumps({'acceptance': row(accept), 'status': decision['status']}))


if __name__ == '__main__':
    main()
