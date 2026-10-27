"""Retry only setup refused before work: create the documented runs parent."""
import importlib.util
import json
from pathlib import Path
import sys

path = Path(__file__).with_name('run-qualification.py')
spec = importlib.util.spec_from_file_location('qualification_wrapper', path)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)
assert not q.RUN.exists()
failure = json.loads((q.OUT / 'full-fixture.command.json').read_bytes())
assert failure['exit'] == 1 and not failure['timed_out'] and failure['owned_group_gone']
assert (q.OUT / 'full-fixture.stderr').read_text() == 'Output refused: Output must be fresh directly under fixed runs directory\n'
assert not (q.CI / 'runs').exists()
(q.CI / 'runs').mkdir()
rows = [json.loads((q.OUT / 'runner-controls.command.json').read_bytes())]
assert rows[0]['exit'] == 0 and rows[0]['owned_group_gone']
rows.append(q.command('full-fixture-2', [sys.executable, '-B', str(q.CI / 'check_cache_state.py'), '--rustc', q.RUSTC, '--out', str(q.RUN)], 690))
receipt = json.loads((q.RUN / 'receipt.json').read_bytes())
assert receipt['status'] == 'passed' and receipt['errors'] == []
assert receipt['cleanup']['removed'] and receipt['cleanup']['groups_returned']
result = {'schema': 1, 'status': 'complete-host-fixture-qualification-passed', 'commands': rows, 'integration_sha256': q.sha(q.OUT / 'integration.json'), 'fixture_receipt': str((q.RUN / 'receipt.json').relative_to(q.ROOT)), 'fixture_receipt_sha256': q.sha(q.RUN / 'receipt.json'), 'receipt_commands': len(receipt['commands']), 'compiler_identity': receipt['rustc'], 'prelaunch_setup_refusal': 'Documented fixed runs parent was absent; first invocation refused before any compiler or test. Created that parent and launched once with unchanged bounds/source.', 'original_CI_failure_remains_failed': True, 'fresh_Rust_1_98_1_CI_pending': True, 'native_runtime_or_GA': False}
with (q.OUT / 'qualification.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result), flush=True)
