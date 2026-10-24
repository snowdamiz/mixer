#!/usr/bin/env python3
"""Exact V4 22+17 tests, with scratch redirected here and no assertion changes."""
import importlib.util
import pathlib
import sys
import types
import unittest
HERE = pathlib.Path(__file__).resolve().parent
V4 = HERE.parent / 'apple-toggle-keyboard-focus-v4'
sys.path.insert(0, str(V4))
source = (V4 / 'test_independent_adapted.py').read_text()
source = source.replace("SCRATCH = HERE / '.scratch'", "SCRATCH = pathlib.Path(" + repr(str(HERE / '.scratch')) + ")")
module = types.ModuleType('test_independent_adapted'); module.__file__ = str(V4 / 'test_independent_adapted.py')
sys.modules[module.__name__] = module
exec(compile(source, module.__file__, 'exec'), module.__dict__)
spec = importlib.util.spec_from_file_location('unchanged_v4_focus', V4 / 'test_v4.py')
focused = importlib.util.module_from_spec(spec); spec.loader.exec_module(focused)
suite = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(module), unittest.defaultTestLoader.loadTestsFromModule(focused)])
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() and result.testsRun == 39 else 1)
