#!/usr/bin/env python3
"""Guarded source-only preparation; no product, compiler or oracle runtime."""
import offline
offline.install()
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'swift-pin-bitmap-match-host-admission'
EXPECTED = 'd1e3be943bb5a15a2e1d0a87d0a8f1e455c42d81594760f1a8dd1257251a9fe1'
assert not (HERE / 'seal.json').exists(), 'Refuse replacing a sealed parser packet'

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

original = (BASE / 'admit.py').read_bytes()
assert sha(original) == EXPECTED, 'Original harness drift'
before = original.decode()
old_tree = ast.parse(before)
old = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'test_evidence')
replacement = (HERE / 'parser_function.py').read_text()
assert len(ast.parse(replacement).body) == 1
assert ast.parse(replacement).body[0].name == old.name
lines = before.splitlines(keepends=True)
after = ''.join(lines[:old.lineno - 1]) + replacement.rstrip() + '\n' + ''.join(lines[old.end_lineno:])
(HERE / 'admit.py').write_text(after)
for name in ('bounded_commands.py',):
    (HERE / name).write_bytes((BASE / name).read_bytes())
new_tree = ast.parse(after)
old_nodes = {n.name: n for n in old_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
new_nodes = {n.name: n for n in new_tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
assert old_nodes.keys() == new_nodes.keys()
changed = [name for name in old_nodes if ast.dump(old_nodes[name], include_attributes=False) != ast.dump(new_nodes[name], include_attributes=False)]
assert changed == ['test_evidence']
old_outside = ast.Module(body=[n for n in old_tree.body if n is not old], type_ignores=[])
new_function = new_nodes['test_evidence']
new_outside = ast.Module(body=[n for n in new_tree.body if n is not new_function], type_ignores=[])
assert ast.dump(old_outside, include_attributes=False) == ast.dump(new_outside, include_attributes=False)
old_source = ast.get_source_segment(before, old)
new_source = ast.get_source_segment(after, new_function)
(HERE / 'admit.py.diff').write_text(''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile='actual-run/admit.py', tofile='proposed/admit.py')))
(HERE / 'local').mkdir(exist_ok=True)
scope = {'schema': 1, 'originalHarnessSHA256': EXPECTED, 'proposedHarnessSHA256': sha(after.encode()),
         'changedTopLevelDefinitions': changed, 'outsideFunctionASTByteIdentical': True,
         'oldFunction': {'lines': [old.lineno, old.end_lineno], 'sourceSHA256': sha(old_source.encode()), 'astSHA256': sha(ast.dump(old, include_attributes=False).encode())},
         'newFunction': {'lines': [new_function.lineno, new_function.end_lineno], 'sourceSHA256': sha(new_source.encode()), 'astSHA256': sha(ast.dump(new_function, include_attributes=False).encode())},
         'unchangedTopLevelDefinitions': [n for n in old_nodes if n not in changed],
         'boundedCommandsByteIdentical': (HERE / 'bounded_commands.py').read_bytes() == (BASE / 'bounded_commands.py').read_bytes(),
         'runtimeRuns': 0, 'guardBeforeSubjectImports': True, 'liveApiAttempts': offline.ATTEMPTS,
         'pythonVersion': sys.version}
save(HERE / 'source-scope.json', scope)
save(HERE / 'local/preparation.json', scope)
assert not offline.ATTEMPTS
print(json.dumps(scope, sort_keys=True))
