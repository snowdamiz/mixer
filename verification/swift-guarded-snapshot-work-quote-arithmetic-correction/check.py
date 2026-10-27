#!/usr/bin/env python3
"""Targeted arithmetic correction checks; no prior harness or product execution."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ORIGINAL = ROOT / 'verification/swift-guarded-snapshot-complete-work-plan'
FINDING = ROOT / 'verification/swift-semantic-adapter-root-review/guarded-snapshot-complete-work-proposal-custody.json'
MAX64 = (1 << 64) - 1
NAMES = ('checked_sum', 'checked_mul', 'emission', 'quote')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def isolated_functions(path):
    parsed = ast.parse(path.read_text())
    selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef) and node.name in NAMES]
    assert {node.name for node in selected} == set(NAMES)
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    namespace = {'MAX64': MAX64}
    exec(compile(module, str(path) + ':isolated-four-pure-functions', 'exec'), namespace)
    return {node.name: node for node in selected}, namespace


def outcome(function, *args):
    try:
        return {'value': function(*args)}
    except (OverflowError, TypeError) as exc:
        return {'exception': type(exc).__name__, 'message': str(exc)}


def run():
    checks = 0
    def require(value):
        nonlocal checks
        assert value
        checks += 1
    def binding(path):
        data = path.read_bytes()
        return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': digest(data)}
    require(digest(FINDING.read_bytes()) == '4486fa022350dec1884713a21c0aa528acb2c8810c72d7b6427690126cb9ec48')
    original_seal = ORIGINAL / 'seal.json'
    require(digest(original_seal.read_bytes()) == '7198ae0748ce0c8c576afc953aef8f3827b0a0d925ea246225245ba4cf000a27')
    seal = json.loads(original_seal.read_text())
    require(seal['member_count'] == 5 and seal['member_bytes'] == 47303)
    for member in seal['members']:
        data = (ORIGINAL / member['path']).read_bytes()
        require(len(data) == member['bytes'] and digest(data) == member['sha256'])
    old_ast, old = isolated_functions(ORIGINAL / 'check.py')
    new_ast, new = isolated_functions(HERE / 'quote.py')
    for name in ('checked_sum', 'emission', 'quote'):
        require(ast.dump(old_ast[name], include_attributes=False) == ast.dump(new_ast[name], include_attributes=False))
    require(not new_ast['quote'].args.defaults)
    require([arg.arg for arg in new_ast['quote'].args.args] == ['ingress', 'setup', 'wasi_finish', 'attached', 'extent', 'blocks', 'dispatch_delta'])
    witness_old = outcome(old['checked_mul'], MAX64, 1)
    witness_new = outcome(new['checked_mul'], MAX64, 1)
    require(witness_old == {'exception': 'OverflowError', 'message': 'u64 addition'})
    require(witness_new == {'value': MAX64})
    scalar_cases = [
        (0, 0, 0), (0, MAX64, 0), (MAX64, 0, 0), (MAX64, 1, MAX64), (1, MAX64, MAX64),
        (MAX64 - 1, 1, MAX64 - 1), (1, MAX64 - 1, MAX64 - 1),
        (MAX64 // 2, 2, MAX64 - 1), (2, MAX64 // 2, MAX64 - 1),
        (1 << 32, (1 << 32) - 1, (1 << 64) - (1 << 32)),
        # Existing checked_sum uses isinstance(int), which accepts bool.
        # Preserve that contract rather than adding unrelated rejection.
        (True, MAX64, MAX64), (MAX64, True, MAX64), (False, MAX64, 0), (True, True, 1),
    ]
    for a, b, expected in scalar_cases:
        require(outcome(new['checked_mul'], a, b) == {'value': expected})
    for a, b in [(MAX64, 2), (2, MAX64), ((MAX64 // 2) + 1, 2), (1 << 32, 1 << 32)]:
        require(outcome(new['checked_mul'], a, b) == {'exception': 'OverflowError', 'message': 'u64 multiplication'})
    invalid = [-1, MAX64 + 1, 1.0, '1', None, [], {}]
    for value in invalid:
        for other in (0, 1):
            require(outcome(new['checked_mul'], value, other) == {'exception': 'OverflowError', 'message': 'invalid u64 input'})
            require(outcome(new['checked_mul'], other, value) == {'exception': 'OverflowError', 'message': 'invalid u64 input'})
    require(outcome(new['checked_sum'], MAX64, 1) == {'exception': 'OverflowError', 'message': 'u64 addition'})
    require(outcome(new['checked_sum'], MAX64, 0) == {'value': MAX64})
    quote_cases = [
        (0, 0, 0, False, 2560, 1, 0),
        (10, 20, 30, False, 2560, 1, 7),
        (10, 20, 30, True, 2560, 1, 7),
        (0, 0, 0, False, 69765152, 17033, 0),
    ]
    for args in quote_cases:
        expected = 451703621 + args[0] + (args[1] + args[2] if args[3] else 0) + args[6] + 16384 + 19537 + 299377 * args[5] + 32 * args[4]
        require(outcome(new['quote'], *args) == {'value': expected})
        require(outcome(old['quote'], *args) == {'value': expected})
    require(new['quote'](*quote_cases[0]) == 452120839)
    try:
        new['quote'](extent=2560, blocks=1, attached=False, dispatch_delta=0)
    except TypeError:
        checks += 1
    else:
        raise AssertionError('required incoming prices became optional')
    require(outcome(new['quote'], MAX64, 0, 0, False, 2560, 1, 0) == {'exception': 'OverflowError', 'message': 'u64 addition'})
    ledger = json.loads((ORIGINAL / 'ledger.json').read_text())
    require(ledger['fixed_prepaid_portion'] == 451703621)
    require(ledger['incoming_ledger_interface'] == ['W_ingress', 'W_setup', 'W_wasi_finish'])
    # Recheck all original members after executing isolated pure functions.
    for member in seal['members']:
        require(digest((ORIGINAL / member['path']).read_bytes()) == member['sha256'])
    return {'schema': 1, 'status': 'targeted-arithmetic-utility-correction-proposed',
            'controls_passed': checks,
            'original_defect_witness': {'a': MAX64, 'b': 1, 'old': witness_old, 'corrected': witness_new},
            'original_binding': binding(original_seal), 'finding_binding': binding(FINDING),
            'corrected_utility': binding(HERE / 'quote.py'),
            'original_members_reverified_unchanged': 5, 'fixed_prefix_unchanged': 451703621,
            'required_incoming_interface_unchanged': ['W_ingress', 'W_setup', 'W_wasi_finish'],
            'checked_sum_emission_quote_ast_unchanged': True,
            'contract': 'Each operand independently satisfies isinstance(int) and 0<=value<=MAX64; multiply then check product<=MAX64; bool remains int-compatible as before',
            'scope': 'Only four AST-extracted pure arithmetic functions from original/correction; no make(), old harness, VM, writer, compiler, native, UI/capture or global process inventory',
            'complete_work_accepted': False, 'product_source_changed': False,
            'native_or_GA_accepted': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    result = run()
    data = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
    path = HERE / 'results.json'
    if args.verify:
        assert path.read_bytes() == data
    else:
        path.write_bytes(data)
    print(json.dumps({'controls_passed': result['controls_passed'], 'original_defect_reproduced': True,
                      'MAX64_times_one_corrected': result['original_defect_witness']['corrected']['value'],
                      'mode': 'verify' if args.verify else 'generate', 'complete_work_accepted': False}, sort_keys=True))


if __name__ == '__main__':
    main()
