#!/usr/bin/env python3
"""Record only this independent finite checker; never invokes prior runners."""
import datetime
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
path = HERE / 'commands.json'
receipt = json.loads(path.read_text()) if path.exists() else {'schema': 1, 'commands': []}
receipt.update({
    'tool': {'executable': sys.executable, 'version': sys.version,
             'system': platform.system(), 'machine': platform.machine()},
    'source_tree_sha256': '575b55d3391729749039dc2badccc9107449cb2c9a021d8ef67282c39b2e1896',
    'scope': 'Only own independent Python finite controls; four AST-extracted pure arithmetic functions; read-only frozen/source review; no frozen builder/make()/harness replay, product/VM/writer/native/hosted/Android/UI/capture execution or process inventory',
    'product_source_or_git_mutated': False, 'owned_native_or_capture_processes_started': 0,
    'temporary_test_instances_created': 0,
})
for arguments in [[], ['--verify']]:
    argv = [sys.executable, str(HERE / 'check.py'), *arguments]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    completed = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
    item = {'argv': argv, 'cwd': str(ROOT), 'started_at': started,
            'script_sha256': hashlib.sha256((HERE / 'check.py').read_bytes()).hexdigest(),
            'exit_code': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr}
    receipt['commands'].append(item)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(item, sort_keys=True))
    if completed.returncode:
        target = HERE / 'attempt-history' / (item['script_sha256'] + '.py')
        target.parent.mkdir(exist_ok=True)
        target.write_bytes((HERE / 'check.py').read_bytes())
        sys.exit(completed.returncode)
