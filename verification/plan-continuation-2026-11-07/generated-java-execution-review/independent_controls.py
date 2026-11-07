"""Pure/fake review controls; all output is confined to this new review directory."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
prior = HERE.parent / 'generated-java-review-r2/independent_controls.py'
spec = importlib.util.spec_from_file_location('prior_review', prior)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
M = review.M
real_compile = M.compile_consumer

def adapted_compile(consumer, destination, profile, jdk, sdk, run, label):
    def adapted_run(command_label, argv, **options):
        M.require(options == ({'stdout_bytes': M.JAVAP_STDOUT_BYTES}
                  if command_label.endswith('-javap-members') else {}), 'Incorrect stdout budget boundary')
        return run(command_label, argv)
    return real_compile(consumer, destination, profile, jdk, sdk, adapted_run, label)

class NewControls(review.IndependentControls):
    def test_new_apple_metadata_change_fails_actual_execute_postflight(self):
        with mock.patch.object(M, 'apple_producer_provenance', side_effect=[{'sdk':'before'}, {'sdk':'after'}]):
            receipt, calls, compiled, _, _ = self.fake_execute()
        self.assertEqual(len(compiled), 6)
        self.assertEqual(receipt['status'], 'failed')
        self.assertEqual(receipt['error'], 'Selected Apple producer SDK changed during integration')
        self.assertTrue(receipt['cleanup']['owned_scratch_removed'])
        self.assertFalse(any(c['label'] == 'official-inspect-postflight' for c in calls))
        self.record('apple_postflight_drift', receipt)

    def test_new_missing_apple_selection_blocks_before_commands(self):
        with mock.patch.object(M, 'tool_environment', return_value=({}, {})), \
             mock.patch.object(M, 'apple_producer_provenance', real_apple), \
             mock.patch.object(M.subprocess, 'Popen', side_effect=AssertionError('must not spawn')):
            receipt = M.execute(review.SimpleNamespace(output=self.root/'missing-apple', execute_toolchains=True))
        self.assertEqual(receipt['status'], 'failed')
        self.assertIn('Explicit per-command', receipt['error'])
        self.assertEqual(receipt['command_records'], [])
        self.assertFalse(receipt['cleanup']['owned_scratch_started'])
        self.record('missing_apple_preflight', receipt)

    def test_new_exact_eight_MiB_output_is_complete(self):
        commands = M.Commands(self.root, review.os.environ.copy(), seconds=15, command_seconds=5)
        size = M.JAVAP_STDOUT_BYTES
        output = commands.run('exact-eight', [sys.executable,'-B','-c',
            'import sys; sys.stdout.buffer.write(b"x"*8388608)'], stdout_bytes=size)
        self.assertEqual(len(output), size)
        self.assertEqual(output, 'x'*size)
        self.assertTrue(commands.custody_terminal())
        self.assertIsNone(commands.records[0]['stop'])
        self.record('exact_eight_MiB', commands.records[0])

real_apple = M.apple_producer_provenance
with mock.patch.object(M, 'apple_producer_provenance', return_value={'fake_boundary': True}), \
     mock.patch.object(M, 'compile_consumer', side_effect=adapted_compile):
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NewControls))
review.FACTS.update({'tests_run':result.testsRun,'passed':result.wasSuccessful(),'optimized':not __debug__,
                    'prior_controls_identity':M.identity(prior),'scope':'Seven unchanged R2 controls with boundary adapters plus three independent review controls; no real compiler/native tools'})
M.save(HERE / ('independent-optimized.json' if not __debug__ else 'independent-normal.json'), review.FACTS)
sys.exit(0 if result.wasSuccessful() else 1)
