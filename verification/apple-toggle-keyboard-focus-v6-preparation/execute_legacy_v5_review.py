#!/usr/bin/env python3
"""Run all 26 sealed V5 review semantics unchanged; only scratch/witness location moves."""
import pathlib
import types
import unittest
HERE=pathlib.Path(__file__).resolve().parent
source=HERE.parent/'apple-toggle-keyboard-focus-v5-independent-review/test_review.py'
module=types.ModuleType('unchanged_v5_independent_review')
# Its existing HERE/ROOT logic now selects only owned scratch/witness paths.
module.__file__=str(HERE/'legacy_v5_review_source.py')
exec(compile(source.read_bytes(),str(source),'exec'),module.__dict__)
result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
raise SystemExit(0 if result.wasSuccessful() else 1)
