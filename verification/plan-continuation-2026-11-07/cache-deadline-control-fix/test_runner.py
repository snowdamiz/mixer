#!/usr/bin/env python3
"""All original 36 runner controls, exact new helper, owned evidence and fake children."""
import argparse
import os
import signal
import sys
import unittest
from local_support import HERE, save, workspace, write_guard
from control_source import control_source


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', default='runner-optimized' if sys.flags.optimize else 'runner-normal')
    parser.add_argument('-v', action='store_true')
    args = parser.parse_args()
    write_guard()
    from adopt_fixture import verify
    proof = verify()
    module, destination = workspace(args.label, control_source())
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    if suite.countTestCases() != 36:
        raise RuntimeError('Original 36-control discovery required')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    save(destination / 'result.json', {'tests': result.testsRun,
        'failures': [(str(case), error) for case, error in result.failures],
        'errors': [(str(case), error) for case, error in result.errors],
        'successful': result.wasSuccessful(), 'adoption': proof,
        'timer_disarmed': signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
        'remaining_test_scratch': [str(p) for p in (destination / 'scratch').iterdir()],
        'scope': 'Python fake children/pure controls on this Mac. No compiler fixture, native or GA qualification.'})
    verify()
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
