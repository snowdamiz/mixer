"""Prospective hosted entrypoint. Never executed by this fake-only campaign."""
import argparse
import json
import signal
import sys
import unittest
from adopt_fixture import HERE, OLD, install, previous, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', action='store_true')
    parser.parse_args()
    proof = verify()
    previous()
    import local_support
    from control_source import control_source
    source = control_source()
    # The old source/helper/seals remain unchanged. Only the evidence destination
    # and runner Commands implementation are selected for the future invocation.
    old_here = local_support.HERE
    old_path = list(sys.path)
    try:
        local_support.HERE = HERE
        local_support.write_guard()
        module, destination = local_support.workspace('original-optimized' if sys.flags.optimize else 'original-normal', source)
        install(module.r)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        if suite.countTestCases() != 36:
            raise RuntimeError('All original 36 controls required')
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        local_support.save(destination / 'result.json', {
            'tests': result.testsRun, 'successful': result.wasSuccessful(),
            'failures': [(str(c), e) for c, e in result.failures],
            'errors': [(str(c), e) for c, e in result.errors], 'adoption': proof,
            'timer_disarmed': signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
            'scope': 'Future original Python controls including real descendants; not executed by premise campaign.'})
    finally:
        local_support.HERE = old_here
        sys.path[:] = old_path
    verify()
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
