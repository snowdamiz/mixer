#!/usr/bin/env python3
"""Data-only exact new-outer MIR/role/control inventory; not work pricing."""
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
from prepare import HERE, write, sha

NAMES = ['selected_outer_request_v1', 'borrow_original_diagnostics_once_v1',
         'observe_borrowed_originals_v1', 'run_selected_one_fixture_outer_v1',
         'consume_outer_request_v1']
CUTS = ['selected_outer_request_v1', 'selected_parent_account_v1',
        'run_one_fixture_v1', 'usage_v1', 'borrow_original_diagnostics_once_v1',
        'inspect_v1', 'observe_borrowed_originals_v1',
        'destroy_returned_fixture_v1', 'release_after_retirement_v1']

def derive():
    path = HERE/'commands/compiler-only-query/outer-and-query.mir'
    text = path.read_text()
    functions = []
    for name in NAMES:
        body = next(part for part in re.split(r'(?=^fn )', text, flags=re.M)
                    if part.startswith('fn '+name+'('))
        header = body.split('\n', 1)[0]
        roles = [{'local': local, 'type': ty, 'kind': 'parameter'} for local, ty in
                 re.findall(r'(_\d+): (.*?)(?=, _\d+:|\) ->)', header)]
        roles += [{'local': local, 'type': ty.strip(), 'kind': 'return-or-local-or-temporary'}
                  for local, ty in re.findall(r'^\s+let(?: mut)? (_\d+): ([^\n]+?);(?: +//|$)', body, re.M)]
        assert len({r['local'] for r in roles}) == len(roles)
        blocks = {}
        for match in re.finditer(r'^    (bb\d+)( \(cleanup\))?: \{\n(.*?)^    \}', body, re.M|re.S):
            block_name, cleanup, raw = match.groups()
            lines = [line.split('//',1)[0].strip() for line in raw.splitlines()]
            code = [line for line in lines if line]
            successors = sorted(set(re.findall(r'\bbb\d+\b', '\n'.join(code))))
            calls = {cut: sum(bool(re.search(r'= .*\b'+cut+r'\(', line)) and ' -> ' in line
                              for line in code) for cut in CUTS}
            blocks[block_name] = dict(cleanup=bool(cleanup), operations=code,
                successors=successors, calls={k:v for k,v in calls.items() if v})
        assert 'bb0' in blocks
        paths = []
        def visit(block_name, prefix):
            assert block_name not in prefix, ('cycle requires explicit bound', name, prefix, block_name)
            block = blocks[block_name]
            current = prefix+[block_name]
            if not block['successors']:
                counts = {cut:sum(blocks[b]['calls'].get(cut,0) for b in current) for cut in CUTS}
                paths.append(dict(blocks=current, calls={k:v for k,v in counts.items() if v},
                    cleanup=any(blocks[b]['cleanup'] for b in current)))
            for successor in block['successors']: visit(successor, current)
        visit('bb0', [])
        functions.append(dict(name=name, MIR_sha256=sha(body.encode()), header=header,
            roles=roles, blocks=blocks, paths=paths,
            direct_call_max={cut:max(p['calls'].get(cut,0) for p in paths) for cut in CUTS}))
    by_name = {f['name']:f for f in functions}
    outer = by_name['consume_outer_request_v1']['direct_call_max']
    borrowed = by_name['borrow_original_diagnostics_once_v1']['direct_call_max']
    assert outer['usage_v1'] == 3
    assert outer['borrow_original_diagnostics_once_v1'] == 1 and borrowed['inspect_v1'] == 1
    for cut in ['run_one_fixture_v1', 'destroy_returned_fixture_v1', 'release_after_retirement_v1']:
        assert outer[cut] == 1
    # Every release-call path traverses the destruction call's normal successor
    # and the Some-token block. Unwind targets do not rejoin a release route.
    out = by_name['consume_outer_request_v1']
    release_paths = [p for p in out['paths'] if p['calls'].get('release_after_retirement_v1')]
    for path in release_paths:
        assert path['calls'].get('destroy_returned_fixture_v1') == 1
        destruction = next(b for b in path['blocks'] if out['blocks'][b]['calls'].get('destroy_returned_fixture_v1'))
        release = next(b for b in path['blocks'] if out['blocks'][b]['calls'].get('release_after_retirement_v1'))
        assert path['blocks'].index(destruction) < path['blocks'].index(release)
        between = path['blocks'][path['blocks'].index(destruction)+1:path['blocks'].index(release)+1]
        assert all(not out['blocks'][b]['cleanup'] for b in between)
    return dict(schema=1, scope='exact retained compiler MIR of five new outer functions only; no old component work repricing',
        compiler_terminal_exit_status='unknown after receipt writer failure',
        input_MIR_sha256=sha(text.encode()), functions=functions,
        function_count=len(functions), roles=sum(len(f['roles']) for f in functions),
        written_operations=sum(len(b['operations']) for f in functions for b in f['blocks'].values()),
        direct_terminal_paths=sum(len(f['paths']) for f in functions),
        finite_new_outer_I_max=1, finite_new_outer_U_max=3,
        inherited_account_component_conditional=2825436,
        new_outer_work_or_storage_price_selected=False,
        native_dynamic_backing_or_compiled_leaf_correspondence=False,
        operational_grant=False)

def main():
    value = derive()
    if '--check-only' in sys.argv:
        assert json.loads((HERE/'outer-mir-inventory.json').read_bytes()) == value
    else: write('outer-mir-inventory.json', value)
    print(json.dumps({k:v for k,v in value.items() if k != 'functions'}, sort_keys=True))

if __name__ == '__main__': main()
