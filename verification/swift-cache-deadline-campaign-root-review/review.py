"""Bounded independent pure audit of the selected second cache experiment."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import signal
import sys
import time
import unittest

signal.alarm(50)
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
PACKET = ROOT / 'verification/swift-cache-deadline-campaign-v2-correction'
SEAL = 'd8079bacfbb5fee222ac55354ad5a9aaa2a320327d50acd181426fea0d46a2d3'
forbidden = []


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
        'os.system', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.exec', 'os.kill', 'os.killpg'
    }:
        forbidden.append(event)
        raise RuntimeError('Forbidden process/socket/custody action: ' + event)


def row(path):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


assert not (OUT / 'receipt.json').exists()
seal = row(PACKET / 'seal.json')
assert seal['sha256'] == SEAL
members = json.loads((PACKET / 'seal.json').read_bytes())['files']
for name, expected in members.items():
    path = PACKET / name
    assert path.resolve().is_relative_to(PACKET.resolve())
    actual = row(path)
    assert {k: actual[k] for k in ('bytes', 'sha256')} == expected
sys.addaudithook(audit)
started = time.monotonic()
spec = importlib.util.spec_from_file_location('independent_deadline_controls', PACKET / 'test_campaign.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with (OUT / 'pure-controls.stdout').open('x') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
assert result.testsRun == 17 and result.wasSuccessful() and not result.skipped
checked = module.campaign.check(OUT / 'source-check')
assert [p['sourceSHA256'] for p in checked['profiles']] == [
    '2f0973fe11f5db5341d2896d0e9a25b30a11687dedea5914547f5897c8161d28',
    'fd27e6b68e3d57226ad14855166a33f359664cd848fcc1918f3b3e265ffc8a39']
assert not forbidden
receipt = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'command': 'python3 -B verification/swift-cache-deadline-campaign-root-review/review.py',
    'python': sys.version, 'elapsed_seconds': time.monotonic() - started, 'alarm_seconds': 50,
    'seal': seal, 'packet_members_rehashed': len(members), 'controls_passed': result.testsRun,
    'forbidden_process_socket_custody_events': forbidden, 'full_attempts_run': 0,
    'finding': 'Frozen v2 inherited-helper exceptions could remove scratch with unproven command closure',
    'correction': 'Explicit pending custody remains across any unproven exception; typed real exit and exact group absence clear it; scratch retained and further commands stop otherwise',
    'harness_clock_review': 'One unchanged Instant feeds RuntimeControl and WASI construction before initialization; both corpus calls use the same original owner and cumulative budgets',
    'profiles': checked['profiles'], 'original_v2_unchanged': True,
    'named_unlock': 'Both exact full corpus calls match all11 original native fields on one owner and consume to zero resources',
    'scope': 'Source and mocked controls accepted for selected bounded remote experiment; actual compilation, finite controls and full outcomes pending',
    'remote_execution_selected': True, 'GA_or_production_profile_accepted': False,
    'workflow': row(PACKET / 'workflow.yml'), 'campaign': row(PACKET / 'campaign.py'),
    'test_output': row(OUT / 'pure-controls.stdout')}
with (OUT / 'receipt.json').open('x') as stream:
    json.dump(receipt, stream, indent=2)
    stream.write('\n')
print(json.dumps({'controls_passed': result.testsRun, 'forbidden_events': forbidden,
                  'profiles': [p['sourceSHA256'] for p in checked['profiles']], 'remote_selected': True}))
