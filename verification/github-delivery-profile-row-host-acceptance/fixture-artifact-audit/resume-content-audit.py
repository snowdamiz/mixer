"""Resume the data-only audit after retaining the exact selection-count diagnosis."""
import json
import sys
from capture import capture, ROOT, digest

assert __debug__
resolution = json.loads((ROOT / 'audit-failure-resolution.json').read_bytes())
assert digest((ROOT / resolution['failed_script']).read_bytes())['sha256'] == resolution['failed_auditor_sha256']
assert digest((ROOT / 'audit-content.py').read_bytes())['sha256'] == resolution['corrected_auditor_sha256']
for path in ROOT.glob('*.command.json'):
    record = json.loads(path.read_bytes())
    assert not record['timed_out']
    assert record['exit_code'] == (1 if path.name in resolution['failed_command_records'] else 0)
    assert digest((ROOT / record['stdout_file']).read_bytes()) == record['stdout']
    assert digest((ROOT / (path.name.removesuffix('.command.json') + '.stderr')).read_bytes()) == record['stderr']
capture('content-audit-corrected', [sys.executable, '-B', str(ROOT / 'audit-content.py')])
report = json.loads((ROOT / 'full-audit.json').read_bytes())
assert report['passed'] and report['source_revision'] == '4e7c21ee82def176bfe857dba2fa243eb8b4ebb1'
assert report['source_tree'] == 'f852f6f8f695c6e953c324d1b5f00c5e291b907d'
print(json.dumps({'passed': True, 'commands': report['commands'], 'focused_controls': report['focused_controls']['tests'], 'actual_compiler_release': report['actual_compiler_release'], 'artifact_sha256': report['artifact_sha256']}))
