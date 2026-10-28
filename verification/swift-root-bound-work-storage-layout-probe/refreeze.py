#!/usr/bin/env python3
"""Preserve the unreleased draft and narrow closure identity to exact pipe span."""
from pathlib import Path
import datetime
import hashlib
import json

D = Path(__file__).resolve().parent
def sha(raw): return hashlib.sha256(raw).hexdigest()
def put(path, obj):
    with path.open('x') as handle: json.dump(obj, handle, indent=2, sort_keys=True); handle.write('\n')
def main():
    assert not (D / 'seal.json').exists() and not (D / 'command').exists() and not (D / 'build').exists()
    previous = D / 'pre-seal-draft-01'; previous.mkdir()
    for name in ['plan.json', 'preparation-receipt.json', 'controls-result.json']: (D / name).rename(previous / name)
    plan = json.loads((previous / 'plan.json').read_text())
    span = dict(plan['diagnostics']['actual_closure']['expression'])
    span.update(byte_end=span['byte_start']+2, line_end=span['line_start'], column_end=span['column_start']+2,
                source_sha256=sha(b'||'), source_text='||')
    plan['diagnostics']['actual_closure']['identity_span'] = span
    for member in plan['scripts']:
        raw = (D / member['path']).read_bytes(); member.update(bytes=len(raw), sha256=sha(raw))
    plan['prepared_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    plan['supersedes_unreleased_pre_seal_draft'] = {'path': 'pre-seal-draft-01/plan.json', 'sha256': sha((previous/'plan.json').read_bytes()),
        'reason': 'Self-review narrowed anonymous closure identity endpoint from a range inside its expression to exactly its physical || token span; source146/three edits/argv/environment unchanged. No compiler or strategy probe ran.'}
    put(D / 'plan.json', plan)
    receipt = json.loads((previous/'preparation-receipt.json').read_text())
    receipt.update(plan_sha256=sha((D/'plan.json').read_bytes()), refreeze_command=['/opt/homebrew/opt/python@3.14/bin/python3.14', '-B', str(D/'refreeze.py')],
                   correction=plan['supersedes_unreleased_pre_seal_draft'])
    put(D/'preparation-receipt.json', receipt)
    print(json.dumps({'status': 'prepared-not-executed', 'plan_sha256': receipt['plan_sha256'], 'source_argv_environment_unchanged': True}))
if __name__ == '__main__': main()
