#!/usr/bin/env python3
"""Verify this reviewable candidate seal and, in CI, its installed workflow."""
import argparse
import json
from pathlib import Path
import materialize_pack as m

HERE = Path(__file__).resolve().parent
WORKFLOW = '.github/workflows/cache-fixture-shared-input-controls-v2.yml'


def verify(installed=False):
    seal = m.load(HERE / 'seal.json')
    rows = seal['members']
    m.need(rows == sorted(rows, key=lambda row: row['path'])
           and len(rows) == len({row['path'] for row in rows}) == seal['member_count']
           and m.tree(rows) == seal['tree_sha256'], 'Candidate seal closure differs')
    for row in rows:
        path = m.regular(HERE / m.member(row['path']))
        m.need(path.stat().st_size == row['bytes'] and m.sha(path) == row['sha256'],
               'Candidate file differs: ' + row['path'])
    # Runtime evidence directories are deliberately outside the shipping seal.
    expected = {row['path'] for row in rows} | {'seal.json'}
    observed = {row['path'] for row in m.inventory(HERE, excluded={
        'logs', 'runs', 'control-scratch', 'materialized', '__pycache__'})}
    m.need(observed == expected, 'Missing/extra shipping candidate member')
    if installed:
        m.need(m.sha(m.regular(m.ROOT / WORKFLOW)) == m.sha(HERE / 'workflow/cache-fixture-shared-input-controls-v2.yml'),
               'Installed workflow differs from sealed manual candidate')
    return {'candidate_tree_sha256': seal['tree_sha256'], 'candidate_member_count': seal['member_count'],
            'workflow_installed_and_bound': installed, 'inputs': m.verify_inputs()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-installed', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.workflow_installed), sort_keys=True))
