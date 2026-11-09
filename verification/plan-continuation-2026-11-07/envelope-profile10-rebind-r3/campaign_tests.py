#!/usr/bin/env python3
"""Run the inherited fake suites and new source-binding controls in one payload."""
from pathlib import Path
import json
import runpy
import sys
HERE = Path(__file__).resolve().parent
results = []
for name, count in [('test_binding.py', 10), ('test_ownership.py', 27), ('test_rebind.py', 12)]:
    sys.argv = [str(HERE / name)]
    try: runpy.run_path(str(HERE / name), run_name='__main__')
    except SystemExit as error:
        status = 0 if error.code is None else error.code
        results.append({'script': name, 'expected_tests': count, 'status': status})
        if status != 0: break
    else: results.append({'script': name, 'expected_tests': count, 'status': 0})
mode = 'optimized' if sys.flags.optimize else 'normal'
(HERE / ('campaign-' + mode + '.json')).write_text(json.dumps({'mode': mode, 'python': sys.version,
    'executable': sys.executable, 'results': results, 'scope': 'Pure/fake, no compiler, native or fixture run'}, indent=2) + '\n')
sys.exit(0 if len(results) == 3 and all(r['status'] == 0 for r in results) else 1)
