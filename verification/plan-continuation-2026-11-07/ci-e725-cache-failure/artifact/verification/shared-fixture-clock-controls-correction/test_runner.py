#!/usr/bin/env python3
"""Run all 36 original controls with the exact mocked-clock helper correction."""
import sys
from adopt_fixture import verify

verify()
from control_source import FROZEN, control_source

_corrected_control_source = control_source()
sys.path.insert(0, str(FROZEN.parent))
# The original unittest.main() must see the actual __main__ module globals.
# Its original HERE, optimized-child cwd and retention paths stay at frozen v2.
globals()['__file__'] = str(FROZEN)
exec(compile(_corrected_control_source, str(FROZEN), 'exec'), globals())
