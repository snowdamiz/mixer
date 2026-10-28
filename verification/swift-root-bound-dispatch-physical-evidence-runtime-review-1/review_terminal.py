#!/usr/bin/env python3
"""Offline review of released saved receipts; never imports the candidate."""
import time
START = time.monotonic()
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path('/Users/andreyyurlov/Documents/dev/mixer')
D = Path(__file__).resolve().parent
RUNNER = ROOT / 'verification/swift-physical-verifier-host-runner-2'
OLD = ROOT / 'verification/swift-physical-verifier-host-runner-1'
LANE = ROOT / 'verification/swift-root-bound-dispatch-physical-evidence-v2'
REVIEW = ROOT / 'verification/swift-root-bound-dispatch-physical-evidence-independent-v2'
RR = ROOT / 'verification/swift-semantic-adapter-root-review'
RUNTIME = RUNNER / 'runtime'
CACHE = {}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read(path):
    assert time.monotonic() - START < 53.5
    path = Path(path)
    if path in CACHE:
        return CACHE[path]
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and path.resolve(strict=True) == path
    assert info.st_size <= 16777216
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        raw = stream.read(info.st_size + 1)
        after = os.fstat(stream.fileno())
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns)
    assert len(raw) == info.st_size and identity(info) == identity(opened) == identity(after)
    CACHE[path] = raw
    return raw

def load(path, expected=None):
    raw = read(path)
    if expected:
        assert sha(raw) == expected, str(path)
    def pairs(items):
        result = {}
        for key, value in items:
            assert key not in result
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))

def row(path):
    raw = read(path)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}

def checked(path, pin):
    actual = row(path)
    assert actual['bytes'] == pin['bytes'] and actual['sha256'] == pin['sha256'], str(path)
    return actual

def members(base, packet):
    entries = packet['members']
    assert len(entries) == packet['member_count']
    assert len({entry['path'] for entry in entries}) == len(entries)
    assert sha(json.dumps(entries, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()) == packet['tree_sha256']
    if 'member_bytes' in packet:
        assert sum(entry['bytes'] for entry in entries) == packet['member_bytes']
    for entry in entries:
        path = Path(entry['path'])
        assert not path.is_absolute() and all(x not in ('', '.', '..') for x in entry['path'].split('/'))
        checked(base / path, entry)

def differences(a, b, path=''):
    if type(a) is not type(b): return [path]
    if type(a) is dict:
        result = []
        for key in sorted(set(a) | set(b)):
            name = path + '/' + key.replace('~', '~0').replace('/', '~1')
            result += [name] if key not in a or key not in b else differences(a[key], b[key], name)
        return result
    if type(a) is list:
        if len(a) != len(b): return [path]
        return [part for index, (left, right) in enumerate(zip(a, b)) for part in differences(left, right, path + '/' + str(index))]
    return [] if a == b else [path]

def save(name, value):
    with (D / name).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')

release_path = RR / 'dispatch-physical-verifier-v2-host-release-2.json'
release = load(release_path, '81507ced606edff31d9d180561d437b76a23640c54dd3ad0f37a8dd6314975fe')
plan = load(RUNNER / 'host-test-plan.json', '49348e2c66677933bca0028324bab7a52e639a894512c62b81bd367ea8f7d475')
base = load(LANE / 'host-test-plan.json', '83fdb4bae803e4f0374307f1302e2ecf4a67c5b37edfbcbc5f97faef1e44786e')
runner = load(RUNNER / 'manifest.json', '804ef53bf8ed7aa46e6ffb1cd2120e088a9cf4001cbf3af98bbf40ba5cdab985')
assert differences(base, plan) == ['/controller_environment', '/root_release_required/path']
assert plan['controller_environment'] == dict(base['environment'], __CF_USER_TEXT_ENCODING='0x1F5:0x0:0x0')
assert plan['root_release_required']['path'] == str(release_path.relative_to(ROOT))
assert len(runner['members']) == runner['member_count'] == 5
assert sum(p['bytes'] for p in runner['members']) == runner['member_bytes']
for entry in runner['members']: checked(RUNNER / entry['path'], entry)
assert release['plan_sha256'] == row(RUNNER / 'host-test-plan.json')['sha256']
assert release['base_plan_sha256'] == row(LANE / 'host-test-plan.json')['sha256']
assert release['runner_manifest_sha256'] == row(RUNNER / 'manifest.json')['sha256']
assert release['controller_sha256'] == row(RUNNER / 'run-synthetic16.py')['sha256']
assert release['python_test_lane_released'] is True and release['python_test_invocations'] == 1
assert release['automatic_retries'] == 0 and release['actual_saved_input_parse_or_capture_released'] is False
assert release['first_preflight_candidate_test_invocations'] == 0
packet = load(LANE / 'seal.json', '866d0058d5f54116f3459bc0fcf4a3afe6437e30f796c69d3759d2de8893bedc')
assert packet['member_count'] == 12 and packet['tree_sha256'] == 'a8f5cd09364bc9146508a4cdab1ac76f5f9496110a6c6ed44854ee069bc04137'
members(LANE, packet)
review = load(REVIEW / 'seal.json', '0ca1c7d76fa013bbf0a93b3f1c9231722822d70de38ce109f1563b268d379f18')
members(REVIEW, review)
review_result = load(REVIEW / 'review-result.json', 'fc0715c8fb230e383f86a2113f3a589bae4c014a3039436d887fe8a64d365bda')
assert review_result['findings'] == [] and review_result['synthetic_host_test_release_recommended'] is True
assert review_result['source_files'] == plan['source_files'] == release['source_files']
assert review_result['host_plan_sha256'] == row(LANE / 'host-test-plan.json')['sha256']
assert review_result['producer_seal_sha256'] == row(LANE / 'seal.json')['sha256']
assert release['independent_source_review'] == dict(row(REVIEW / 'seal.json'), path=str((REVIEW / 'seal.json').relative_to(ROOT)))
manifest = load(LANE / 'input-manifest.json')
roster = load(LANE / 'test-family-map.json')
expected_pins = {}
def expect(path, pin=None):
    actual = row(path) if pin is None else checked(path, pin)
    assert actual['path'] not in expected_pins or expected_pins[actual['path']] == actual
    expected_pins[actual['path']] = actual
for path in [LANE/'host-test-plan.json', RUNNER/'host-test-plan.json', LANE/'seal.json', REVIEW/'seal.json', release_path, RUNNER/'manifest.json']:
    expect(path)
for folder, sealed in [(LANE, packet), (REVIEW, review)]:
    for entry in sealed['members']: expect(folder/entry['path'], entry)
for entry in manifest['inputs'] + plan['source_files']: expect(ROOT/entry['path'], entry)
for entry in runner['members']: expect(RUNNER/entry['path'], entry)
expect(Path(plan['python_tool']['path']), plan['python_tool'])
receipt = load(RUNTIME / 'receipt.json')
observation = load(RUNTIME / 'observations.json')
assert receipt['status'] == 'passed'
assert receipt['observations_sha256'] == row(RUNTIME/'observations.json')['sha256']
assert receipt['observations_sha256'] == 'e3b3a1472072b5d8c8506ccdbb610501185637de1f247d827b85de67c936f548'
for name in ['plan_sha256','base_plan_sha256','packet_seal_sha256','controller_sha256']:
    assert receipt[name] == release[name] == observation[name]
assert observation['runner_manifest_sha256'] == release['runner_manifest_sha256']
assert observation['packet_tree_sha256'] == packet['tree_sha256']
assert observation['independent_source_review_sha256'] == row(REVIEW/'seal.json')['sha256']
assert observation['pins_before'] == observation['pins_after'] == sorted(expected_pins.values(), key=lambda item: item['path'])
assert observation['all_pins_rechecked'] is True and observation['errors'] == []
assert receipt['observed_signals'] == receipt['finalization_errors'] == []
assert observation['owned_groups_closed'] is True and observation['automatic_retries'] == 0
assert observation['python_version'] == base['python_version_from_this_preparation']
assert observation['python_tool'] == base['python_tool']
assert observation['controller_environment'] == plan['controller_environment']
assert observation['allowed_plan_diff'] == ['/controller_environment', '/root_release_required/path']
assert len(observation['commands']) == 1
command = observation['commands'][0]
assert command['kind'] == 'synthetic16'
assert command['argv'] == base['argv'] and command['environment'] == base['environment'] and command['cwd'] == base['cwd']
assert sha(json.dumps(command['argv'], sort_keys=True, separators=(',', ':')).encode()) == base['argv_sha256_canonical_JSON']
assert command['custody'] is True and command['pid'] == command['pgid'] == command['sid'] == 45721
assert command['cleanup_path'] == 'completed-child-no-signals'
proof = command['completion_observation']
assert proof['pid'] == command['pid'] and proof['code'] == 1 and proof['status'] == 0
assert command['reaped'] is True and command['returncode'] == 0 and command['group_absent'] is True
assert command.get('signals', []) == [] and not command.get('permission_refusal') and not command.get('syscall_errors')
assert command.get('custody_uncertain', False) is False
assert command['full_streams_captured'] is True and not command.get('output_truncated')
bounds = base['bounds']
assert bounds['wall_seconds'] == 55 and bounds['test_deadline_seconds'] == 44 and bounds['owned_cleanup_deadline_seconds'] == 49 and bounds['posthash_deadline_seconds'] == 53.5
assert 0 < command['start_seconds'] < proof['seconds'] <= command['reap_seconds'] <= command['group_absent_seconds'] <= command['end_seconds'] < bounds['test_deadline_seconds']
assert command['end_seconds'] < observation['elapsed_before_observation_seconds'] < receipt['signal_cutoff_seconds'] < bounds['posthash_deadline_seconds']
for name in ['stdout','stderr']:
    stream = command[name]
    assert stream['file'] == 'host-tests.' + name
    raw = read(RUNTIME / stream['file'])
    assert len(raw) == stream['bytes'] <= bounds['maximum_' + name + '_bytes'] and sha(raw) == stream['sha256']
assert read(RUNTIME/'host-tests.stdout') == b''
families = roster['families']
assert [item['family'] for item in families] == ['P%02d' % i for i in range(1,17)]
names = [item['test_method'] for item in families]
assert len(names) == len(set(names)) == 16
tests_text = read(LANE/'source/tests_region_certificate.py').decode()
assert re.findall(r'^    def (test_p\d+_[a-z0-9_]+)\(self\):', tests_text, re.M) == names
stderr = read(RUNTIME/'host-tests.stderr').decode('utf-8')
expected_lines = [name + ' (__main__.RegionCertificateControls.' + name + ') ... ok' for name in names]
lines = stderr.splitlines()
assert len(lines) == 21 and lines[:16] == expected_lines
assert lines[16] == lines[19] == '' and lines[17] == '-'*70 and lines[20] == 'OK'
assert re.fullmatch(r'Ran 16 tests in [0-9]+\.[0-9]{3}s', lines[18])
assert stderr == '\n'.join(expected_lines) + '\n\n' + '-'*70 + '\n' + lines[18] + '\n\nOK\n'
assert observation['passing_methods'] == names and observation['tests_passed'] == 16
assert observation['generated'] == {'file_bytes':0,'member_count':1,'members':[{'bytes':0,'path':'tmp','type':'directory'}]}
assert observation['generated_directory_removed'] is True
assert not os.path.lexists(base['owned_outputs']['directory'])
for data in [release, receipt, observation, packet]:
    assert data.get('physical_capacity_prices_backings_root_funding_product_GA_accepted', False) is False
    assert data.get('complete_capacity_accepted', False) is False
assert receipt['all_results_local_geometry_only'] is observation['all_results_local_geometry_only'] is True
assert "synthetic=True" in tests_text and "if __name__=='__main__':unittest.main(verbosity=2)" in tests_text
assert 'def scoped(self,result):' in tests_text
# Source assessment of finalization order, with no import or syntax execution.
controller = read(RUNNER/'run-synthetic16.py').decode()
tail = controller[controller.index('        save("observations.json", outcome)'):]
assert tail.index('observations_sha = digest(') < tail.index('signal.pthread_sigmask(signal.SIG_BLOCK, SIGNALS)') < tail.index('cutoff = time.monotonic() - START') < tail.index('signal.sigpending()') < tail.index('save("receipt.json"')
assert tail.count('digest(') == 1 and tail.count('verify_pins(') == 0
assert 'later signals outside this receipt' in receipt['signal_scope']
# Preserve the first refusal as a refusal, not an unsuccessful candidate test.
attempt_path = RR/'dispatch-physical-verifier-v2-host-attempt-1.json'
attempt = load(attempt_path)
assert attempt['status'] == 'preflight-refused-before-test-launch' and attempt['controller_exit'] == 1
assert attempt['candidate_imports_or_tests'] == 0 and attempt['owned_child_or_group_created'] is False
assert attempt['runtime_or_command_directories_created'] is False and attempt['automatic_retry'] is False
checked(ROOT/attempt['release']['path'], attempt['release'])
checked(ROOT/attempt['controller']['path'], attempt['controller'])
old_manifest = load(OLD/'manifest.json', runner['previous_attempt_provenance']['previous_runner_manifest_sha256'])
for entry in old_manifest['members']: checked(OLD/entry['path'], entry)
assert runner['previous_attempt_provenance']['previous_release_sha256'] == attempt['release']['sha256']
assert runner['previous_attempt_provenance']['previous_runner_controller_sha256'] == attempt['controller']['sha256']
assert attempt['separate_diagnostic']['invocations'] == 1
assert attempt['separate_diagnostic']['observed_environment'] == plan['controller_environment']
assert attempt['separate_diagnostic']['provided_environment'] == base['environment']
# Read current bytes again without the cache to detect a change during this review.
before = [row(path) for path in sorted(CACHE)]
cached = dict(CACHE)
CACHE.clear()
for path, raw in cached.items(): assert read(path) == raw, str(path)
after = [row(path) for path in sorted(CACHE)]
assert before == after and time.monotonic() - START < 53.5
save('checked-inputs.json', {'before':before,'after':after,'equal':True,'runtime_pins_reconstructed':len(expected_pins)})
result = {
 'schema':1,'status':'FROZEN_INDEPENDENT_TERMINAL_REVIEW_SYNTHETIC16_HOST_PASS_ONLY',
 'at':datetime.now(timezone.utc).isoformat(),'findings':[],
 'command':[str(Path(sys.executable).resolve()),'-B',str(Path(__file__).resolve())],
 'review_script_sha256':sha(Path(__file__).read_bytes()),'review_python':sys.version,
 'elapsed_seconds':time.monotonic()-START,'checked_input_members':len(before),
 'before_after_custody_equal':True,'runtime_pins_reconstructed':len(expected_pins),
 'root_release':row(release_path),'runner_manifest':row(RUNNER/'manifest.json'),
 'base_plan':row(LANE/'host-test-plan.json'),'amended_plan':row(RUNNER/'host-test-plan.json'),
 'producer_seal':row(LANE/'seal.json'),'producer_tree_sha256':packet['tree_sha256'],
 'independent_source_review':row(REVIEW/'seal.json'),
 'root_receipt':row(RUNTIME/'receipt.json'),'root_observation':row(RUNTIME/'observations.json'),
 'first_refusal':row(attempt_path),'first_refusal_preserved':True,
 'first_attempt_candidate_imports_or_tests':0,'separate_stdlib_environment_diagnostic_reported':1,
 'candidate_test_invocations':1,'methods':names,'passed':16,'failed':0,'skipped':0,
 'unittest_reported_seconds':float(lines[18].split()[4][:-1]),
 'root_signal_cutoff_seconds':receipt['signal_cutoff_seconds'],
 'child':{'pid':command['pid'],'exit':0,'cleanup_path':command['cleanup_path'],'completion':proof,
          'reaped':True,'group_absent':True,'active_signals':[]},
 'owned_generated_directory_removed':True,'all_runtime_pins_rechecked':True,
 'source_files':plan['source_files'],'source146_binding':'91bab68a8aef4a7cbe300af0fca8145462e08dcaaef2631f42a0d2d55748bd8f',
 'accepted_boundary':'Exactly one synthetic-only Python host invocation passed all16 frozen control methods against the reviewed two-file v2 verifier;the root controller records exact-child closure,capped complete streams,bounded owned-tree cleanup and unchanged pins.',
 'recommendation':'Accept the corrected offline verifier synthetic host slice only. Any real compile capture,whole-function semantic map,independent review and trusted root approval still require separate exact plans/releases.',
 'limits':[
  'Synthetic positive/adverse records are not actual compiler geometry or physical capacity evidence.',
  'Provided child environment is the unchanged seven-key plan;the controller effective eight-key environment was recorded. The child effective environment was not separately reported.',
  'Prior preflight refusal remains retained;the separate stdlib-only diagnostic is root-recorded evidence,not a candidate invocation.',
  'Finite receipt scope ends at the one-way cutoff after all hashing;no later-signal handling claim.',
  'Generated-tree cleanup concerns only the owned tree;no kernel sandbox or absence of writes elsewhere is claimed.',
  'No actual saved-input verification,capture,compiler,model,native runtime,work price,backing bound,root funding,product integration or GA is accepted.'
 ],
 'this_review_candidate_import_syntax_test_parser_actual_compiler_capture_runtime_or_process_probe_actions':0,
 'this_review_product_metadata_commit_push_actions':0,
 'all_results_local_geometry_only':True,'complete_capacity_accepted':False,
 'physical_capacity_prices_backings_root_funding_product_GA_accepted':False
}
save('review-result.json', result)
print(json.dumps({'status':result['status'],'methods':16,'runtime_pins':len(expected_pins),'checked_inputs':len(before),'elapsed_seconds':result['elapsed_seconds']}))
