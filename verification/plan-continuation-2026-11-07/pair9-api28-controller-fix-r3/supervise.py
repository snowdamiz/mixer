"""Accepted lifecycle supervises exactly two fake-host control invocations."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

OUT = Path(__file__).resolve().parent
PACKET = OUT
spec = importlib.util.spec_from_file_location('accepted_review_cleanup', PACKET/'cleanup_control.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)
out = OUT/'corrected-control-supervisor'; out.mkdir(exist_ok=False)
scratch = out/'scratch'; scratch.mkdir()
manager = c.Commands(out, dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
    deadline=time.monotonic()+250, output_bytes=4*c.MIB, total_output_bytes=32*c.MIB)
receipt = {'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'status': 'failed',
    'maximumInvocations': 2, 'maximumSecondsPerInvocation': 120, 'outputBytes': 4*c.MIB, 'totalOutputBytes':32*c.MIB}
try:
    for mode in ('normal', 'optimized'):
        argv = [sys.executable, '-B', *(['-O'] if mode=='optimized' else []), OUT/'host_controls.py']
        manager.run(mode, argv, OUT, 120)
    receipt['status'] = 'passed'
except BaseException as error:
    receipt['error'] = repr(error)
finally:
    receipt['cleanup'] = manager.cleanup(scratch)
    receipt['commands'] = manager.records
    if not receipt['cleanup']['allTerminalCustody']: receipt['status']='failed'
    (out/'receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
print(json.dumps({'status':receipt['status'], 'invocations':len(manager.records), 'cleanup':receipt['cleanup']}))
sys.exit(0 if receipt['status']=='passed' else 1)
