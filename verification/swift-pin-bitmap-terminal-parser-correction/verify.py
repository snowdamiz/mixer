#!/usr/bin/env python3
"""Guarded source/seal checks; never run product commands."""
import offline
offline.install()
import ast
import difflib
import hashlib
import json
from pathlib import Path
import sys
import admit as a
import bounded_commands as b

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'swift-pin-bitmap-match-host-admission'
MEMBERS = {'.gitignore', 'PROPOSAL.md', 'admit.py', 'admit.py.diff', 'bounded_commands.py',
           'offline.py', 'parser_function.py', 'prepare.py', 'replay.py', 'freeze.py',
           'source-scope.json', 'receipt.json', 'verify.py'}

def row(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def tree(rows):
    return hashlib.sha256(''.join(n + '\0' + rows[n]['sha256'] + '\n' for n in sorted(rows)).encode()).hexdigest()

def check(sealed=True):
    before, after = (BASE / 'admit.py').read_text(), (HERE / 'admit.py').read_text()
    assert row(BASE / 'admit.py')['sha256'] == 'd1e3be943bb5a15a2e1d0a87d0a8f1e455c42d81594760f1a8dd1257251a9fe1'
    old_tree, new_tree = ast.parse(before), ast.parse(after)
    old = next(n for n in old_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'test_evidence')
    new = next(n for n in new_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'test_evidence')
    assert ast.get_source_segment(after, new) == (HERE / 'parser_function.py').read_text().rstrip()
    original_lines = before.splitlines(keepends=True)
    assert ''.join(original_lines[:old.lineno - 1]) + ast.get_source_segment(after, new) + '\n' + ''.join(original_lines[old.end_lineno:]) == after
    assert ast.dump(ast.Module(body=[n for n in old_tree.body if n is not old], type_ignores=[]), include_attributes=False) == ast.dump(ast.Module(body=[n for n in new_tree.body if n is not new], type_ignores=[]), include_attributes=False)
    expected_diff = ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True), fromfile='actual-run/admit.py', tofile='proposed/admit.py'))
    assert (HERE / 'admit.py.diff').read_text() == expected_diff
    assert row(HERE / 'bounded_commands.py') == row(BASE / 'bounded_commands.py')
    assert row(HERE / 'bounded_commands.py')['sha256'] == '93cc3c4ae578a3f5bf01c09cd143859c48ee3e7b473f9c8f34ead1f60724bee9'
    assert (HERE / '.gitignore').read_text() == 'local/\noutputs/\n__pycache__/\n'
    scope = b.json_data((HERE / 'source-scope.json').read_bytes())
    assert scope['changedTopLevelDefinitions'] == ['test_evidence'] and scope['outsideFunctionASTByteIdentical']
    for key, node, source in (('oldFunction', old, before), ('newFunction', new, after)):
        assert scope[key]['sourceSHA256'] == hashlib.sha256(ast.get_source_segment(source, node).encode()).hexdigest()
        assert scope[key]['astSHA256'] == hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
    assert scope['proposedHarnessSHA256'] == row(HERE / 'admit.py')['sha256']
    manifest, data = a.inputs()
    assert len(data) == 136 and len(a.OVERLAYS) == 15 and a.closure(manifest['candidateFiles']) == a.CANDIDATE == 'e9282e05cea70d4aceaf6a145fb9f971acb023dd41a7d4651216753666305ba1'
    assert (a.ACTIVE_SECONDS, a.CLEANUP_SECONDS, b.MAX_COMMANDS, b.OUTPUT_CAP, b.AGGREGATE_OUTPUT_CAP) == (1800, 60, 6, 8388608, 33554432)
    assert b.subprocess.Popen is b.os.waitpid is b.os.killpg is a.signal.setitimer is offline.denied
    assert not offline.ATTEMPTS
    if sealed:
        seal = b.json_data((HERE / 'seal.json').read_bytes())
        assert set(seal['files']) == MEMBERS
        for name, expected in seal['files'].items():
            assert row(HERE / name) == expected, 'Sealed parser member drift: ' + name
        assert tree(seal['files']) == seal['treeSHA256']
        actual = {p.relative_to(HERE).as_posix() for p in HERE.rglob('*') if p.is_file()
                  and p.relative_to(HERE).parts[0] not in {'local', 'outputs', '__pycache__'} and p.name != 'seal.json'}
        assert actual == MEMBERS
    return {'schema': 1, 'changedDefinitions': ['test_evidence'], 'outsideFunctionASTByteIdentical': True,
            'candidateMembers': 136, 'overlays': 15, 'candidateTreeSHA256': a.CANDIDATE,
            'sealed': sealed, 'subjectRuntimeRuns': 0, 'guardBeforeSubjectImports': True,
            'liveApiAttempts': offline.ATTEMPTS, 'pythonVersion': sys.version}

if __name__ == '__main__':
    print(json.dumps(check(), sort_keys=True))
