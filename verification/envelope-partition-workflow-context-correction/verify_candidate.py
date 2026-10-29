#!/usr/bin/env python3
"""Guarded filesystem-only corrected-closure verification; no official validator."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
import offline_guard
offline_guard.install(HERE)
import ast
import hashlib
import json
import admission
import context_placement

PARENT_SEAL = '057e500afa3ee57e0469e377c3c4f947053e1fe163f258f52e57ccc80cd5be73'
RULES = '6bacc2888c658bf306fba4b668e04f8ea59219122ac187ae9065d9f2d75c89b4'


def verify(installed=False, review_seal=True):
    admission.verify_sources(installed=installed, review_seal=review_seal)
    raw = admission.raw(HERE / 'frozen-parent-seal.json')
    admission.need(admission.digest(raw) == PARENT_SEAL, 'Frozen parent seal differs')
    parent = json.loads(raw)
    rows = parent['members']
    admission.need(rows == sorted(rows, key=lambda row: row['path']) and
                   len(rows) == parent['member_count'] == len({r['path'] for r in rows}) == 9 and
                   admission.digest(admission.canonical(rows)) == parent['tree_sha256'] and
                   sum(r['bytes'] for r in rows) == parent['total_bytes'], 'Frozen parent tree differs')
    basis = json.loads(admission.raw(HERE / 'correction-basis.json'))
    admission.need(basis['frozen_parent']['seal_sha256'] == PARENT_SEAL, 'Correction parent differs')
    by_name = {r['path']: r for r in rows}
    for name in ('admission.py', 'offline_guard.py', 'review_controls.py', 'source-bindings.json',
                 'workflow-proposal.yml'):
        local = 'frozen-parent-workflow.yml' if name == 'workflow-proposal.yml' else name
        data = admission.raw(HERE / local)
        admission.need(len(data) == by_name[name]['bytes'] and
                       admission.digest(data) == by_name[name]['sha256'], 'Copied parent member differs: ' + name)
    admission.need(admission.digest(admission.raw(HERE / 'context-rules.json')) == RULES ==
                   basis['official_context_evidence']['sha256'], 'Frozen context evidence differs')
    parser = admission.raw(HERE / 'context_placement.py').decode()
    functions = {node.name: ast.get_source_segment(parser, node) for node in ast.parse(parser).body
                 if isinstance(node, ast.FunctionDef)}
    for name, expected in basis['data_parser_source']['functions'].items():
        admission.need(admission.digest(functions[name].encode()) == expected,
                       'Frozen data-parser function differs: ' + name)
    current = context_placement.parse(admission.raw(HERE / 'workflow-proposal.yml').decode())
    original = context_placement.parse(admission.raw(HERE / 'frozen-parent-workflow.yml').decode())
    result = context_placement.validate_contract(current, original)
    admission.need(offline_guard.DENIED == [], 'Runtime operation attempted')
    return {**result, 'passed': True, 'corrected_closure_seal_verified': review_seal,
            'installed_workflow_matches': installed, 'frozen_parent_seal_sha256': PARENT_SEAL,
            'workflow_sha256': admission.digest(admission.raw(HERE / 'workflow-proposal.yml')),
            'denied_runtime_attempts': offline_guard.DENIED}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.installed), sort_keys=True))
