#!/usr/bin/env python3
"""Independent offline review. No child, socket, PID action, or runtime probe."""
import ast
import contextlib
import copy
import hashlib
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
tempfile.tempdir = str(OUT)
denied_events = []


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {
        'os.system', 'os.fork', 'os.forkpty', 'os.posix_spawn', 'os.exec',
        'os.kill', 'os.killpg', 'os.startfile', 'os.spawn', 'pty.spawn',
    }:
        denied_events.append(event)
        raise RuntimeError('Independent review forbids process/socket/PID action: ' + event)


sys.addaudithook(audit)
signal.alarm(50)


def row(body):
    return {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_json(path):
    return json.loads((ROOT / path).read_bytes())


spec = importlib.util.spec_from_file_location('reviewed_canonical_controls', ROOT / 'hosted/scripts/test_identity_network_collector.py')
canonical = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = canonical
spec.loader.exec_module(canonical)
subject = canonical.collector


def metadata():
    values = {}
    old = 'verification/identity-production-network-contract/'
    for name in ('contract.json', 'packet-manifest.json'):
        values[old + name] = (ROOT / old / name).read_bytes()
    for label in ('elixir', 'postgres'):
        for suffix in ('index', 'amd64-manifest', 'amd64-config'):
            name = old + 'inputs/registry/' + label + '-' + suffix + '.json'
            values[name] = (ROOT / name).read_bytes()
    for base in ('verification/identity-network-image-amendment-v1/metadata/',
                 'verification/identity-network-image-amendment-v2/metadata/'):
        manifest = read_json(base + 'packet-manifest.json')
        for name in [*manifest['files'], 'packet-manifest.json']:
            values[base + name] = (ROOT / base / name).read_bytes()
    return values


def observation(role='prepare'):
    entries = [
        '301 280 0:81 / /workspace rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=983040k',
        '302 301 0:82 / /workspace/tooling rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=65536k',
        '303 280 0:83 / /tmp rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=65536k',
    ]
    modes = {'/workspace': 0o755, '/workspace/tooling': 0o755, '/tmp': 0o1777}
    if role == 'test':
        entries.append('304 280 0:84 / /run rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=16384k')
        modes['/run'] = 0o755
    return {'role': role, 'source': '/proc/self/mountinfo', 'read_bytes': 4000,
            'read_sha256': 'c' * 64, 'selected_lines': entries, 'path_modes': modes}


SHA = 'b51946058fbe4aa823185bfe27204be59be439982ac3a3e1dbd9f8260b9af046fcfdfbd9066283c3fbba5a2a45dc3570550c12a9a548daf223b80cac222a6d0f'


def transfer(size=8192):
    result = {'source': '/workspace/downloads/rebar3', 'destination': '/workspace/tooling/rebar3',
              'download_bytes': size, 'copied_bytes': size, 'target_bytes': size, 'sha512': SHA,
              'exclusive_create': True, 'closed_before_hash': True, 'owned_download_removed': True}
    download = {'url': 'https://builds.hex.pm/installs/1.18.4/rebar3-3.28.0-otp-29', 'bytes': size, 'sha512': SHA}
    return result, download


class IndependentControls(unittest.TestCase):
    def test_closed_metadata_actual_and_extra_namespace(self):
        data = metadata()
        self.assertEqual(104, len(data))
        subject.validate_execution_metadata(data)
        for name in ('verification/identity-network-image-amendment-v2/metadata/extra',
                     'verification/identity-network-image-amendment-v2/metadata/../overlay',
                     'verification/identity-network-image-amendment-v2/metadata-extra/overlay'):
            changed = dict(data)
            changed[name] = b'{}'
            with self.subTest(name=name), self.assertRaises(subject.CollectorError):
                subject.validate_execution_metadata(changed)

    def test_every_new_packet_byte_and_prior_raw_seal_are_pinned(self):
        data = metadata()
        names = [n for n in data if n.startswith('verification/identity-network-image-amendment-v2/metadata/')]
        names.append('verification/identity-network-image-amendment-v1/metadata/packet-manifest.json')
        for name in names:
            changed = dict(data)
            changed[name] += b'\n'
            with self.subTest(name=name), self.assertRaises(subject.CollectorError):
                subject.validate_execution_metadata(changed)

    def test_actual_mount_order_and_equivalent_exact_units(self):
        for role in ('prepare', 'test'):
            value = observation(role)
            for order in itertools.permutations(value['selected_lines']):
                changed = copy.deepcopy(value)
                changed['selected_lines'] = list(order)
                subject.validate_mount_observation(role, changed)
            for unit in ('67108864', '64m', '64M', '65536K'):
                changed = copy.deepcopy(value)
                changed['selected_lines'][1] = changed['selected_lines'][1].replace('65536k', unit)
                subject.validate_mount_observation(role, changed)

    def test_tooling_superblock_noexec_and_security_contradictions_fail(self):
        for option in ('noexec', 'ro', 'suid', 'dev'):
            value = observation()
            value['selected_lines'][1] = value['selected_lines'][1].replace('rw,size=', 'rw,' + option + ',size=')
            with self.subTest(option=option), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)

    def test_non_tooling_exec_contradictions_fail_in_either_option_set(self):
        for index in (0, 2, 3):
            for location in ('rw,nosuid', 'rw,size='):
                value = observation('test')
                replacement = 'rw,exec,nosuid' if location == 'rw,nosuid' else 'rw,exec,size='
                value['selected_lines'][index] = value['selected_lines'][index].replace(location, replacement)
                with self.subTest(index=index, location=location), self.assertRaises(subject.CollectorError):
                    subject.validate_mount_observation('test', value)

    def test_extra_descendants_are_refused_below_every_selected_path(self):
        for path in ('/workspace/child', '/workspace/tooling/child', '/tmp/child', '/run/child'):
            value = observation('test')
            value['selected_lines'].append('305 302 0:85 / ' + path + ' rw,nosuid,nodev - tmpfs tmpfs rw,size=1k')
            with self.subTest(path=path), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('test', value)

    def test_escaped_or_prefix_neighbor_paths_cannot_replace_mounts(self):
        for path in ('/workspace/tooling2', '/workspace/tooling/child', '/workspace/./tooling', '/workspace/tooling\\040', '/workspace\\057tooling'):
            value = observation()
            value['selected_lines'][1] = value['selected_lines'][1].replace('/workspace/tooling', path)
            with self.subTest(path=path), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)

    def test_mount_id_collision_or_wrong_parent_fails(self):
        for replacement in ('301 301', '302 280', '302 302', '0 301'):
            value = observation()
            value['selected_lines'][1] = value['selected_lines'][1].replace('302 301', replacement)
            with self.subTest(replacement=replacement), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)

    def test_capacity_ambiguity_and_duplicate_flags_fail(self):
        for old, new in (('size=65536k', 'size=65536k,size=64m'), ('size=65536k', 'size=65537k'),
                         ('size=65536k', 'size=64%'), ('rw,nosuid,nodev', 'rw,nosuid,nodev,nodev'),
                         ('rw,size=', 'rw,,size=')):
            value = observation()
            value['selected_lines'][1] = value['selected_lines'][1].replace(old, new)
            with self.subTest(new=new), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)

    def test_selected_modes_special_bits_and_extra_keys_fail(self):
        for role in ('prepare', 'test'):
            for path in observation(role)['path_modes']:
                for mode in (True, 0o777, 0o4755, 0o2755):
                    value = observation(role)
                    value['path_modes'][path] = mode
                    with self.subTest(role=role, path=path, mode=mode), self.assertRaises(subject.CollectorError):
                        subject.validate_mount_observation(role, value)
            value = observation(role)
            value['path_modes']['/unexpected'] = 0o755
            with self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation(role, value)

    def test_mount_read_and_selected_line_bounds_fail_closed(self):
        for field, changed in (('read_bytes', 65537), ('read_bytes', 0), ('read_bytes', 1.0), ('read_bytes', True), ('read_sha256', 'C' * 64)):
            value = observation()
            value[field] = changed
            with self.subTest(field=field, changed=changed), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)
        for suffix in ('\n', '\r', '\t', ' ' * 4096):
            value = observation()
            value['selected_lines'][0] += suffix
            with self.subTest(suffix=repr(suffix[:4])), self.assertRaises(subject.CollectorError):
                subject.validate_mount_observation('prepare', value)

    def test_transfer_exact_lower_and_upper_bound_and_closed_shape(self):
        for size in (1, 16777216):
            value, download = transfer(size)
            subject.validate_rebar_transfer(value, download)
        value, download = transfer()
        value['fallback'] = 'rename'
        with self.assertRaises(subject.CollectorError):
            subject.validate_rebar_transfer(value, download)

    def test_transfer_true_is_not_integer_and_sizes_are_exact_integers(self):
        for field in ('exclusive_create', 'closed_before_hash', 'owned_download_removed'):
            for wrong in (1, 0, 'true', None):
                value, download = transfer()
                value[field] = wrong
                with self.subTest(field=field, wrong=wrong), self.assertRaises(subject.CollectorError):
                    subject.validate_rebar_transfer(value, download)
        for size in (0, -1, 16777217, True, 8192.0, '8192'):
            value, download = transfer(size)
            with self.subTest(size=size), self.assertRaises(subject.CollectorError):
                subject.validate_rebar_transfer(value, download)

    def test_transfer_target_hash_download_and_paths_must_join(self):
        for field, wrong in (('source', '/tmp/rebar3'), ('destination', '/workspace/rebar3'),
                             ('target_bytes', 8191), ('copied_bytes', 8191), ('sha512', '0' * 128)):
            value, download = transfer()
            value[field] = wrong
            with self.subTest(field=field), self.assertRaises(subject.CollectorError):
                subject.validate_rebar_transfer(value, download)
        for field, wrong in (('url', 'https://builds.hex.pm/other'), ('sha512', '0' * 128), ('bytes', 8191)):
            value, download = transfer()
            download[field] = wrong
            with self.subTest(download_field=field), self.assertRaises(subject.CollectorError):
                subject.validate_rebar_transfer(value, download)

    def test_helper_source_uses_read_only_self_mountinfo_and_no_process_or_mount(self):
        text = subject.MOUNTS_EXS
        for required in ('source = "/proc/self/mountinfo"', 'IO.binread(io, 65_537)',
                         'byte_size(data) <= 65_536', ':ok = File.close(io)',
                         'path == selected_path or String.starts_with?(path, selected_path <> "/")'):
            self.assertIn(required, text)
        for forbidden in ('System.cmd', ':os.cmd', ':erlang.open_port', 'mount(', 'File.write', 'File.rm'):
            self.assertNotIn(forbidden, text)

    def test_transfer_literal_order_is_complete_closed_hashed_then_removed_chmod_direct_exec(self):
        text = subject.BOOTSTRAP_EXS
        tokens = ['source = "/workspace/downloads/rebar3"', 'size: source_bytes',
                  'source_bytes > 0 and source_bytes <= 16_777_216', 'rebar_bytes = File.read!(source)',
                  '^source_bytes = byte_size(rebar_bytes)', ':crypto.hash(:sha512, rebar_bytes)',
                  'File.open(target, [:write, :binary, :exclusive])', 'IO.binwrite(target_io, rebar_bytes)',
                  ':ok = File.close(target_io)', 'size: ^source_bytes', ':crypto.hash(:sha512, File.read!(target))',
                  '"' + SHA + '" = target_sha', ':ok = File.rm(source)',
                  'File.chmod!("/workspace/tooling/rebar3", 0o755)',
                  'System.cmd("/workspace/tooling/rebar3", ["--version"]']
        offsets = [text.index(token) for token in tokens]
        self.assertEqual(sorted(offsets), offsets)
        self.assertNotIn('File.rename', text)
        self.assertNotIn('File.cp', text)


def source_checks():
    expected_roots = {
        'verification/identity-production-network-contract': 'a3a806d83e285213df4c0e951282686dcfcfa81701e8005040d5172b3300050d',
        'verification/identity-network-image-amendment-v1': 'c6116eb09de8bdd75ac3f3036c469efed7e11f6beef4210e9577ff9b72cd392c',
        'verification/identity-network-image-amendment-v1/metadata': '9ddc12c8277b120dcd8ef7577dd9da03d245b8502802db85399a6f1104bcbdc8',
        'verification/identity-network-image-amendment-v2/metadata': '0e35cd6dcc1685b16745def4fe0217fc60e5d703c95a5cddbfd2409381c63b6d',
        'verification/github-delivery-blocker-campaign/network-review': '5fdd6d383517487f5df12cbd81086da7e8c0e713fd63fcbd026ce78389b2e293',
    }
    seals = {}
    for name, expected in expected_roots.items():
        packet = read_json(name + '/packet-manifest.json')
        assert packet['tree_digest_sha256'] == digest(packet['files']) == expected
        for path, expected_row in packet['files'].items():
            assert row((ROOT / name / path).read_bytes()) == expected_row, name + '/' + path
        seals[name] = {'files': len(packet['files']), 'tree_digest_sha256': expected, 'all_members_rehashed': True}
    bindings = read_json('verification/identity-network-image-amendment-v2/implementation/source-bindings.json')
    assert digest(bindings) == '65b12100be7470e42761042bfe572ce799952bd04c3d40dba3042d1224fbdb5c'
    for path, expected in bindings.items():
        assert row((ROOT / path).read_bytes()) == expected
    def methods(path):
        text = (ROOT / path).read_text()
        return {c.name + '.' + node.name: ast.get_source_segment(text, node) for c in ast.parse(text).body
                if isinstance(c, ast.ClassDef) for node in c.body
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')}
    suffix = 'hosted/scripts/test_identity_network_collector.py'
    actual = methods(suffix)
    original = methods('verification/identity-network-image-amendment-v1/implementation/before/' + suffix)
    prior = methods('verification/identity-network-image-amendment-v2/implementation/before/' + suffix)
    assert len(original) == 68 and all(actual[k] == v for k, v in original.items())
    changed = [k for k, v in prior.items() if actual[k] != v]
    assert changed == ['CollectorMethodWiringControls.test_collect_requires_actual_prepare_result_before_bootstrap']
    protected = {'.github/workflows/hosted.yml': 'fafd2560cc385a4113ea140bf2d4445d456e1f7f396539dfe2c3e7d6302e8b57',
                 'hosted/lib/mixer_hosted/browser_auth/store.ex': '8c314b1d3ce288a6dc617251233796bd0a9d8894247ccb15b101e1292e513299',
                 'THIRD_PARTY.yml': '27b3d9becb46e9207903119f00c634276033fa595709f65c87276acab5ff7085'}
    for path, sha in protected.items():
        assert row((ROOT / path).read_bytes())['sha256'] == sha
    workflow = (ROOT / '.github/workflows/identity-network.yml').read_text()
    assert workflow.count("      - 'verification/identity-network-image-amendment-v2/**'") == 2
    assert workflow.count('            /verification/identity-network-image-amendment-v2/metadata/**') == 1
    for bad in ('workflow_dispatch', 'schedule:', 'secrets.', 'pull_request_target', 'contents: write'):
        assert bad not in workflow
    return {'seals': seals, 'canonical_bindings': bindings, 'canonical_tree_digest_sha256': digest(bindings),
            'original_68_method_bodies_unchanged': True, 'prior_v1_unchanged_methods': 83,
            'changed_prior_method': changed[0], 'new_canonical_methods': len(actual) - len(prior),
            'protected_and_inventory_sha256': protected, 'workflow_input_and_trigger_scope': 'pass'}


def run_suite(suite, filename):
    with (OUT / filename).open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
            'skipped': len(result.skipped), 'passed': result.wasSuccessful(), 'log': filename}


started = time.monotonic()
sources = source_checks()
canonical_result = run_suite(unittest.defaultTestLoader.loadTestsFromModule(canonical), 'canonical-controls.log')
independent_result = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls), 'independent-controls.log')
result = {'schema': 1, 'python': sys.version, 'alarm_seconds': 50, 'elapsed_seconds': time.monotonic() - started,
          'canonical_controls': canonical_result, 'independent_controls': independent_result,
          'sources': sources, 'forbidden_process_socket_pid_audit_events': denied_events,
          'scope': 'offline source and pure acceptance controls; no Elixir/Docker/compiler/PG/native/custody/runtime execution',
          'cleanup': 'test TemporaryDirectories restricted to this review directory and removed by test contexts',
          'passed': canonical_result['passed'] and independent_result['passed'] and not denied_events}
(OUT / 'verification-result.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
print(json.dumps(result, sort_keys=True, indent=2))
raise SystemExit(0 if result['passed'] else 1)
