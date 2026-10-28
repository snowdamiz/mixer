"""In-process production admission tests; subprocess/compilers/custody denied."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import signal
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent
events = []


def audit(event, args):
    if event.startswith(('subprocess.', 'socket.')) or event in {'os.system', 'os.fork', 'os.forkpty', 'os.kill', 'os.killpg', 'os.posix_spawn'}:
        events.append(event)
        raise RuntimeError('Forbidden process/socket/custody operation: ' + event)


sys.addaudithook(audit)
signal.alarm(40)
spec = importlib.util.spec_from_file_location('axis_pair_fixture', ROOT / 'cli/build-tests/test_android_sdk_compatibility.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class PairDeltaTests(fixture.CompatibilityFixture, unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-axis-pair-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.initialize_compatibility(Path(self.temporary.name).resolve())

    def refuses_before_tools(self, message):
        with mock.patch.object(self.module, 'inspect', side_effect=AssertionError('tools before rejection')), \
             mock.patch.object(self.module, 'checked_output', side_effect=AssertionError('output before rejection')):
            with self.assertRaisesRegex(RuntimeError, message):
                self.module.build(self.root)
        self.assertFalse((self.root / '.mixer').exists())

    def test_previous_profile_lock_rejected_before_source_reads(self):
        self.lock_value['android']['profile']['id'] = 'mixer.android-source-pair.4'
        (self.root / 'mixer.lock').write_text(json.dumps(self.lock_value))
        with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('source before profile')):
            self.refuses_before_tools('android.sdk-profile-mismatch')

    def test_previous_compiled_profile_is_not_a_supported_driver(self):
        old = json.loads((OUT / 'previous-profile.json').read_bytes())
        with mock.patch.object(self.module, 'SOURCE_PROFILE_HEX', json.dumps(old).encode().hex()):
            self.refuses_before_tools('not rendered or supported')

    def drift(self, name):
        path = self.sdk / 'Sources/MixerUI' / name
        data = bytearray(path.read_bytes())
        data[0] ^= 1
        path.write_bytes(data)
        self.refresh_lock()
        self.refuses_before_tools('source compatibility rejected')

    def test_reviewed_authoring_same_length_drift_rejects_recomputed_lock(self):
        self.drift('Authoring.swift')

    def test_reviewed_validator_same_length_drift_rejects_recomputed_lock(self):
        self.drift('Validation.swift')

    def test_extra_UI_source_still_rejects_before_pinned_reads(self):
        (self.sdk / 'Sources/MixerUI/Unselected.swift').write_bytes(b'unselected source')
        self.refresh_lock()
        with mock.patch.object(self.module, 'pinned_read', side_effect=AssertionError('source before closure')):
            self.refuses_before_tools('source compatibility rejected')


suite = unittest.TestSuite()
for name in ['test_exact_relocated_pair_passes_before_tool_sentinel',
    'test_raw_import_inspect_inventory_independent_and_raw_build_refuses',
    'test_invalid_name_and_resources_still_refuse_before_output']:
    suite.addTest(fixture.SourcePairTests(name))
suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(PairDeltaTests))
stream = io.StringIO()
with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
signal.alarm(0)
output = stream.getvalue()
with (OUT / 'pure-controls.stdout').open('x') as target:
    target.write(output)
receipt = {'schema': 1, 'tests_run': result.testsRun, 'failures': len(result.failures),
    'errors': len(result.errors), 'skips': len(result.skipped), 'forbidden_events': events,
    'scope': 'Three existing in-process admission methods and five fresh profile/source integrity controls; no CLI child path or Swift compiler executed',
    'source_profile': fixture.PROFILE['id'], 'sdk_digest': fixture.PROFILE['sdk_compatibility_sha256'],
    'python': sys.version, 'stdout_sha256': hashlib.sha256(output.encode()).hexdigest(),
    'remote_full_CLI_and_Python_suites_pending': True}
with (OUT / 'pure-controls.json').open('x') as target:
    json.dump(receipt, target, indent=2)
    target.write('\n')
print(json.dumps(receipt))
assert result.wasSuccessful() and result.testsRun == 8 and not events
