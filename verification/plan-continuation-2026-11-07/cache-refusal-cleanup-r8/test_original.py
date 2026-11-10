"""All 36 original controls, with a lifecycle-independent accounting fake clock."""
import argparse
import json
import signal
import sys
import unittest
from adopt_fixture import HERE, OLD, install, previous, verify


def trace_descendant_permission_origin(control):
    """Observe only the cooperative descendant test; retain no frames or locals."""
    def observed(case):
        origin = None
        previous_trace = sys.gettrace()
        if previous_trace is not None:
            return control(case)

        def trace(frame, event, argument):
            nonlocal origin
            frame.f_trace_lines = False
            frame.f_trace_opcodes = False
            if origin is None and event == 'exception':
                kind, error, traceback = argument
                if isinstance(error, PermissionError):
                    number = OSError.errno.__get__(error)
                    origin = {
                        'diagnostic': 'cache-descendant-first-permission-error',
                        'filename': frame.f_code.co_filename[:512],
                        'function': frame.f_code.co_name[:128],
                        'line': traceback.tb_lineno,
                        'errno': number if type(number) is int and -2147483648 <= number <= 2147483647 else None,
                    }
            return trace if origin is None else None

        try:
            sys.settrace(trace)
            return control(case)
        finally:
            sys.settrace(previous_trace)
            if origin is not None:
                print(json.dumps(origin, ensure_ascii=True, separators=(',', ':')),
                      file=sys.stderr, flush=True)

    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-v', action='store_true')
    parser.parse_args()
    proof = verify()
    previous()
    import local_support
    from control_source import control_source
    from original_adapter import adapt, proof as adapter_proof
    from stdin_guard import write_guard
    original = control_source()
    source = adapt(original)
    # The old source/helper/seals remain unchanged. Only the evidence destination
    # and runner Commands implementation are selected for the future invocation.
    old_here = local_support.HERE
    old_path = list(sys.path)
    try:
        local_support.HERE = HERE
        write_guard(HERE)
        module, destination = local_support.workspace('original-optimized' if sys.flags.optimize else 'original-normal', source)
        install(module.r)
        from original_safety import attach
        module.RunnerControls.test_owned_descendant_group_is_stopped = (
            trace_descendant_permission_origin(
                module.RunnerControls.test_owned_descendant_group_is_stopped))
        safety = attach(module, destination)
        local_support.save(destination / "source-identity.json", adapter_proof(original))
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        if suite.countTestCases() != 36:
            raise RuntimeError('All original 36 controls required')
        result = unittest.TextTestRunner(verbosity=2, resultclass=safety.result_class).run(suite)
        local_support.save(destination / 'result.json', {
            'tests': result.testsRun, 'successful': result.wasSuccessful(),
            'failures': [(str(c), e) for c, e in result.failures],
            'errors': [(str(c), e) for c, e in result.errors], 'adoption': proof,
            'timer_disarmed': signal.getitimer(signal.ITIMER_REAL) == (0.0, 0.0),
            'inner_custody': safety.summary(),
            'expected_tests': 36, 'complete_original_suite': result.testsRun == 36,
            'scope': 'Actual executed test count above; suite-owned tiny Python children only. No compiler, native, or hosted qualification.'})
    finally:
        local_support.HERE = old_here
        sys.path[:] = old_path
    verify()
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
