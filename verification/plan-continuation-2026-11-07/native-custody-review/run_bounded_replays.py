"""Own only the two permitted fake-test interpreter groups; stop on unknown."""
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'native-custody-premise'))
from cleanup_control import Commands

results = []
for mode in ('normal', 'optimized'):
    out = HERE / mode
    out.mkdir(exist_ok=False)
    scratch = out / 'outer-scratch'
    scratch.mkdir()
    command = [sys.executable, '-B', *(['-O'] if mode == 'optimized' else []), str(HERE / 'replay_fake.py')]
    manager = Commands(out, dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                       deadline=time.monotonic() + 120, output_bytes=4*1024*1024,
                       total_output_bytes=32*1024*1024, cleanup_seconds=5)
    result = {'mode': mode, 'command': command, 'maximumSeconds': 120}
    try:
        manager.run('fake-suite', command, scratch, timeout=115)
        result['status'] = 'passed'
    except BaseException as error:
        result['status'] = 'failed'
        result['error'] = repr(error)
    finally:
        result['cleanup'] = manager.cleanup(scratch)
        result['commands'] = manager.records
        results.append(result)
        (HERE / 'outer-custody.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('mode', 'status', 'cleanup')}), flush=True)
    if manager.hold or not result['cleanup']['allTerminalCustody'] or result['status'] != 'passed':
        break
sys.exit(0 if len(results) == 2 and all(r['status'] == 'passed' and r['cleanup']['allTerminalCustody'] for r in results) else 1)
