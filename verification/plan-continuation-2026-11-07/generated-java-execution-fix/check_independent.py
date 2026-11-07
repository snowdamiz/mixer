"""Rerun unchanged R2 controls with explicit adapters for new runner boundaries."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
source = HERE.parent / 'generated-java-review-r2/independent_controls.py'
spec = importlib.util.spec_from_file_location('prior_r2_controls', source)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
real_compile = review.M.compile_consumer


def adapted_compile(consumer, destination, profile, jdk, sdk, run, label):
    def adapted_run(command_label, argv, **options):
        review.M.require(options == ({'stdout_bytes': review.M.JAVAP_STDOUT_BYTES}
                         if command_label.endswith('-javap-members') else {}), 'Incorrect command budget selection')
        return run(command_label, argv)
    return real_compile(consumer, destination, profile, jdk, sdk, adapted_run, label)


with mock.patch.object(review.M, 'apple_producer_provenance', return_value={'fake_boundary': True}), \
     mock.patch.object(review.M, 'compile_consumer', side_effect=adapted_compile):
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(review.IndependentControls))
review.FACTS.update({'tests_run': result.testsRun, 'passed': result.wasSuccessful(),
                    'optimized': not __debug__, 'original_controls': review.M.identity(source),
                    'adaptation': 'New Apple metadata reader mocked at the existing fake execute boundary; old fake run callback adapted after asserting the exact new javap stdout keyword; original R2 source and assertions unchanged'})
review.M.save(HERE / ('independent-optimized-facts.json' if not __debug__ else 'independent-normal-facts.json'), review.FACTS)
sys.exit(0 if result.wasSuccessful() else 1)
