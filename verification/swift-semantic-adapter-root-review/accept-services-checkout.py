"""Root acceptance of the independently reviewed six-line services CI change."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
REVIEW = ROOT / 'verification/ci-services-sparse-checkout-independent'
OUT = HERE / 'services-checkout-root-check'
ACCEPT = HERE / 'services-sparse-checkout-host-acceptance.json'
assert not OUT.exists() and not ACCEPT.exists()
OUT.mkdir()
sha = lambda b: hashlib.sha256(b).hexdigest()
def row(p):
    data = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}
def save(p, data):
    with p.open('x') as stream: json.dump(data, stream, indent=2); stream.write('\n')
assert row(REVIEW / 'seal.json')['sha256'] == '6bae587208e85ebf4f7c9ddaa9687a713053436fe9e8887f7d0e82960aa47e5d'
argv = [sys.executable, '-B', str(REVIEW / 'audit.py'), '--check']
env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
save(OUT / 'plan.json', {'argv': argv, 'environment': env, 'cwd': str(ROOT), 'timeout_seconds': 45,
    'python': sys.version, 'python_sha256': sha(Path(sys.executable).resolve().read_bytes()),
    'script': row(Path(__file__).resolve()), 'review_seal': row(REVIEW / 'seal.json'),
    'workflow': row(ROOT / '.github/workflows/verify.yml'),
    'source_commit': '9398732c23648a82097d5a72b02b1c77af818e41'})
start = time.monotonic()
child = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
timed = False
try:
    stdout, stderr = child.communicate(timeout=45)
except subprocess.TimeoutExpired:
    timed = True
    os.killpg(child.pid, signal.SIGTERM)
    try: stdout, stderr = child.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate(timeout=5)
try:
    os.killpg(child.pid, 0)
    absent = False
except ProcessLookupError:
    absent = True
for name, data in [('stdout', stdout), ('stderr', stderr)]:
    with (OUT / name).open('xb') as stream: stream.write(data)
save(OUT / 'receipt.json', {'argv': argv, 'exit': child.returncode, 'timed_out': timed,
    'elapsed_seconds': time.monotonic() - start, 'owned_pid': child.pid, 'owned_pgid': child.pid,
    'owned_child_reaped': child.returncode is not None, 'owned_group_absent': absent,
    'outputs': [row(OUT / n) for n in ['stdout', 'stderr']], 'plan': row(OUT / 'plan.json')})
assert child.returncode == 0 and not timed and absent
result = json.loads(stdout)
assert result['members'] == 27 and result['bytes'] == 155133 and result['source_files'] == 153
review = json.loads((REVIEW / 'review.json').read_bytes())
assert review['result'] == 'accept-checkout-selection-with-explicit-limits'
assert review['independent_control_methods'] == 12 and len(review['linux_packages']) == 6
save(ACCEPT, {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'root-accepted-services-CI-sparse-checkout-selection',
    'root_check': row(OUT / 'receipt.json'), 'independent_review': row(REVIEW / 'review.json'),
    'independent_seal': row(REVIEW / 'seal.json'), 'selected_files': 153, 'selected_bytes': 4379716,
    'independent_controls': 12, 'linux_packages': review['linux_packages'],
    'existing_commands_toolchain_timeout_preserved': True,
    'producer_focused_test_positive_and_intended_negative_audited': True,
    'historical_producer_numeric_PID_PGID_unavailable': True,
    'fresh_reviewer_and_root_exact_groups_reaped_and_absent': True,
    'remote_changed_workflow_pending': True, 'full_services_race_suite_not_repeated_locally': True,
    'native_product_operational_OTA_GA_accepted': False})
print(json.dumps(row(ACCEPT)))
