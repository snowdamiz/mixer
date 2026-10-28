#!/usr/bin/env python3
"""Text/hash-only review of the exact root controller. No import or execution."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

D = Path(__file__).resolve().parent
R = D.parents[2]
P = R / 'verification/swift-semantic-adapter-root-review/run-dispatch-region-model-v2.py'
started = time.monotonic()
raw = P.read_bytes()
assert len(raw) == 10258
assert hashlib.sha256(raw).hexdigest() == 'e7bf73dc8f7816a651c0b987f0efd5b2db59e0e3fff9be92c59a56f469717433'
text = raw.decode('utf-8')
plan_path = R / 'verification/swift-root-bound-dispatch-region-model-v2/host-test-plan.json'
plan_raw = plan_path.read_bytes()
assert hashlib.sha256(plan_raw).hexdigest() == '5a2950e97e714e3628546d9b73aa2918c72f23f1221c64806823f978dc2c32e8'
plan = json.loads(plan_raw)
assert plan['bounds']['wall_seconds'] == 55 and plan['bounds']['compiler_invocations'] == plan['bounds']['host_test_invocations'] == 1
assert plan['bounds']['maximum_generated_bytes'] == 33554432 and plan['bounds']['maximum_generated_members'] == 64
assert text.index('buffers = command(plan["commands"][1]') < text.index('generated = []')
assert text.index('"sha256": digest(path, 49)') < text.index('assert len(generated) <= 64')
assert text.index('observed = SEEN +') < text.index('cutoff = time.monotonic() - START')
assert 'signal.signal(sig, signal.SIG_IGN)' in text
assert text.index('plan = json.loads((LANE / "host-test-plan.json").read_bytes())') < text.index('assert digest(LANE / "host-test-plan.json", 30) == PLAN_SHA')
assert 'manifest = json.loads((LANE / "input-manifest.json").read_bytes())' in text
assert 'expected = {"tests::" + x["rust_test"] for x in json.loads((LANE / "test-family-map.json").read_bytes())["families"]}' in text
assert text.count('input-manifest.json') == text.count('test-family-map.json') == 1
assert 'os.WEXITED | os.WNOHANG | os.WNOWAIT' in text
assert text.index('for sig, grace in') < text.index('child.wait(timeout=0)')
assert 'record["pid"] == record["pgid"] == record["sid"]' in text
assert 'ERRORS.append("cleanup: " + repr(error))' in text and 'ERRORS.append("post: " + repr(error))' in text
assert 'passed = not ERRORS and not observed' in text
assert P.read_bytes() == raw and plan_path.read_bytes() == plan_raw
with (D / 'controller-reviewed.py.txt').open('xb') as stream:
    stream.write(raw)
findings = [
    {'id': 'C01', 'priority': 1, 'source_lines': [167, 168, 169, 170, 193, 197, 198, 199],
     'issue': 'Generated-tree bounds and symlink/type inventory run only after the host binary has executed. Before launch the controller only hashes binary; that follows symlinks and applies no32MiB/64-member check. The later inventory hashes a file before testing its declared total size and eagerly sorts an unbounded traversal.',
     'minimum_fix': 'After compiler closure and before binary launch, perform a bounded no-symlink generated-tree inventory. Count members and accumulate regular-file sizes before hashing;refuse over limit or unexpected types immediately. Validate/hash the regular binary from that bounded inventory,then launch it. Retain a bounded post-run/cleanup inventory and preserve artifacts on ambiguity.'},
    {'id': 'C02', 'priority': 1, 'source_lines': [210, 211, 212, 213, 214, 215, 216, 218],
     'issue': 'The cutoff timestamp is assigned after sigpending is sampled. A blocked signal arriving after the snapshot but before cutoff is a pre-cutoff signal absent from observed;installing SIG_IGN can discard it and allow passed. No explicit post-cutoff observation scope is retained,and observations hashing occurs after cutoff.',
     'minimum_fix': 'Use the reviewed one-way finite-cutoff protocol:finish command/cleanup/source/binary/generated hashes and observations digest first;assign cutoff before the protected signal snapshot,or use explicit record-only pre/post-cutoff handlers with an equivalent no-gap boundary. Pre-cutoff observations reject;later signals are expressly outside the completed observation. No compiler/hash/parse follows cutoff;receipt publication alone follows.'},
    {'id': 'C03', 'priority': 1, 'source_lines': [137, 138, 147, 148, 152, 155, 159, 160, 161, 162, 173],
     'issue': 'Control bytes used for execution and roster selection are not all pinned. Plan bytes are parsed before a separate path rehash;input-manifest and test-family-map are parsed without their sealed expected digests,and neither is added to before/after pins. Thus all_pins_rechecked does not establish custody of the actual control data used.',
     'minimum_fix': 'Anchor the exact frozen v2 seal/member roster in the root release/controller. Bounded-read control bytes,verify those same bytes against sealed lengths/digests before parsing/using them,and retain plan,manifest,test roster and other preparation/control-file pins in pre/post custody. Derive the24 distinct expected names from the verified roster;reject duplicate JSON keys or member/path collisions.'}
]
report = {'schema': 1, 'at': datetime.now(timezone.utc).isoformat(),
    'status': 'FROZEN_INDEPENDENT_ROOT_CONTROLLER_SOURCE_REVIEW_CORRECTION_REQUIRED',
    'controller': {'path': str(P.relative_to(R)), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
    'host_plan_sha256': hashlib.sha256(plan_raw).hexdigest(),
    'source_binding': '91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
    'command': [sys.executable, '-B', str(Path(__file__).relative_to(R))], 'cwd': str(R),
    'python': sys.version,
    'python_tool': {'reported_path': sys.executable, 'resolved_path': str(Path(sys.executable).resolve()),
        'sha256': hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()},
    'review_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'controller_imported_or_executed': False, 'compiler_model_test_runtime_version_process_inventory_native_actions': 0,
    'root_execution_release_recommended': False, 'findings': findings,
    'nonblocking_source_observations': ['Two command calls are serial and the second follows successful expected compile exit;absolute offsets share START.',
        'stdout/stderr retained buffers are capped,and output-cap failures propagate through ERRORS.',
        'The child is retained before custody checks;WNOWAIT observation precedes all group signaling;leader is reaped only after signals finish.',
        'Unknown closure,cleanup failure and posthash failure append ERRORS,which gates passed;source review does not establish runtime availability or success.'],
    'before_after_controller_and_plan_bytes_equal': True,
    'scope': 'Three concrete controller blockers only;no new model-source change requested. No runtime,compiler,test,producer replay,canonical metadata,commit or push.',
    'elapsed_seconds': time.monotonic() - started}
assert report['elapsed_seconds'] < 55
with (D / 'review-result.json').open('x') as stream:
    json.dump(report, stream, indent=2, sort_keys=True)
    stream.write('\n')
print(json.dumps({'status': report['status'], 'findings': [row['id'] for row in findings],
                  'root_execution_release_recommended': False, 'elapsed_seconds': report['elapsed_seconds']}))
