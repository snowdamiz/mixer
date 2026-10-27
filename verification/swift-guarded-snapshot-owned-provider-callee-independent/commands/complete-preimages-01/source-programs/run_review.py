"""Bounded independent-review runner. Never imports producer code."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OWN = Path(__file__).resolve().parent
CANDIDATE = ROOT / 'verification/swift-guarded-snapshot-owned-provider-callee-interfaces'
RELEASES = {
    'verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-callee-interfaces-frozen-release.json': 'cd2b48e2f6aa4fc81eaeec126cf3ff5f88ded5bdaf5d8277796afb6cbff3e3ff',
    'verification/swift-semantic-adapter-root-review/guarded-snapshot-owned-provider-work-storage-host-acceptance.json': '64f53d4ee70bb98b7684bc3dcf1f53b5e5b86c34c1a82a2930d362cdcc9d647a',
}

def digest(path):
    body = path.read_bytes()
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {'path': name, 'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}

def custody():
    lock = json.loads((CANDIDATE / 'input-lock.json').read_text())
    seal = json.loads((CANDIDATE / 'seal.json').read_text())
    expected = {x['path']: x for x in lock['files']}
    for row in seal['members']:
        p = str((CANDIDATE / row['path']).relative_to(ROOT))
        expected[p] = dict(row, path=p)
    expected[str((CANDIDATE / 'seal.json').relative_to(ROOT))] = {
        'path': str((CANDIDATE / 'seal.json').relative_to(ROOT)), 'bytes': 39208,
        'sha256': 'e98916beff1a3c8b912e96591fbd573b8d570aa38cc4390a13fa20658290dce0'}
    for p, h in RELEASES.items():
        expected[p] = {'path': p, 'bytes': (ROOT / p).stat().st_size, 'sha256': h}
    actual = [digest(ROOT / p) for p in sorted(expected)]
    differences = [{'expected': expected[r['path']], 'actual': r} for r in actual if r != expected[r['path']]]
    listed = {r['path'] for r in seal['members']}
    present = {str(p.relative_to(CANDIDATE)) for p in CANDIDATE.rglob('*') if p.is_file()} - {'seal.json'}
    result = {'input_count': len(lock['files']), 'candidate_member_count': len(seal['members']),
              'candidate_bytes': sum(r['bytes'] for r in seal['members']),
              'records': actual, 'differences': differences,
              'candidate_membership_extra': sorted(present - listed),
              'candidate_membership_missing': sorted(listed - present)}
    packets = []
    for packet in lock['frozen_packets']:
        directory = ROOT / packet['path']
        old_seal = json.loads((directory / 'seal.json').read_text())
        members = old_seal['members']
        listed_old = {x['path'] for x in members}
        present_old = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()} - {'seal.json'}
        envelope_ok = (digest(directory / 'seal.json')['sha256'] == packet['seal_sha256']
                       and len(members) == packet['members']
                       and sum(x['bytes'] for x in members) == packet['bytes'])
        packets.append({'path':packet['path'],'envelope_ok':envelope_ok,
                        'extra':sorted(present_old-listed_old),'missing':sorted(listed_old-present_old)})
    result['frozen_complete_packet_membership'] = packets
    result['ok'] = (not differences and not result['candidate_membership_extra'] and not result['candidate_membership_missing']
                    and all(x['envelope_ok'] and not x['extra'] and not x['missing'] for x in packets))
    return result

def main():
    name, script, *args = sys.argv[1:]
    out = OWN / 'commands' / name
    out.mkdir(parents=True, exist_ok=False)
    script_path = OWN / script
    sources = [digest(p) for p in sorted(OWN.glob('*.py'))]
    (out / 'source-programs').mkdir()
    for record in sources:
        (out / 'source-programs' / Path(record['path']).name).write_bytes((ROOT / record['path']).read_bytes())
    before = custody()
    (out / 'inputs-before.json').write_text(json.dumps(before, indent=2) + '\n')
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C', 'LANG': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    argv = [sys.executable, '-B', str(script_path), *args]
    receipt = {'schema': 1, 'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'cwd': str(ROOT), 'argv': argv, 'env': env, 'timeout_seconds': 55,
               'python': sys.version, 'executable': digest(Path(sys.executable)),
               'source_files': sources,
               'source_tree_sha256': hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
               'runner_pid': os.getpid(), 'runner_pgid': os.getpgid(0), 'preflight_ok': before['ok']}
    if not before['ok']:
        receipt['child_spawned'] = False
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        raise SystemExit('frozen input custody failed before spawn')
    start = time.monotonic()
    with (out / 'stdout').open('wb') as stdout, (out / 'stderr').open('wb') as stderr:
        child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
        receipt.update(child_spawned=True, child_pid=child.pid, child_pgid=child.pid)
        try:
            receipt['exit_code'] = child.wait(timeout=55)
            receipt['timed_out'] = False
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            receipt['exit_code'] = child.wait()
            receipt['timed_out'] = True
    receipt['elapsed_seconds'] = time.monotonic() - start
    try:
        os.killpg(child.pid, 0)
    except ProcessLookupError:
        receipt['owned_process_group_absent_after_reap'] = True
    else:
        os.killpg(child.pid, signal.SIGKILL)
        receipt['owned_process_group_absent_after_reap'] = False
    after = custody()
    (out / 'inputs-after.json').write_text(json.dumps(after, indent=2) + '\n')
    receipt['postflight_ok'] = after['ok']
    receipt['same_custody_before_after'] = before == after
    receipt['outputs'] = [digest(out / p) for p in ['stdout', 'stderr', 'inputs-before.json', 'inputs-after.json']]
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print((out / 'stdout').read_text())
    print((out / 'stderr').read_text(), file=sys.stderr)
    print(json.dumps({k: v for k, v in receipt.items() if k in ['exit_code', 'elapsed_seconds', 'postflight_ok', 'same_custody_before_after', 'owned_process_group_absent_after_reap']}))
    raise SystemExit(0 if receipt['exit_code'] == 0 and after['ok'] and before == after and receipt['owned_process_group_absent_after_reap'] else 1)

if __name__ == '__main__':
    main()
