#!/usr/bin/env python3
"""Explicit diagnostic source selection; installed tools are supplied by the caller.

This entry reuses frozen bootstrap.run_integration, not hosted bootstrap.main.
Historical source118 admission stays available and intentionally rejects this runner.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
SELECTION = ROOT / 'verification/android-inspection-diagnostic-r1470/selection.json'
RUNNER = 'scripts/ci/check-android-generated-java.py'
BOOTSTRAP = 'verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py'
ENTRY = 'scripts/ci/check-android-generated-java-diagnostic.py'
HISTORICAL = 'verification/plan-continuation-2026-11-07/source113-inspection-caller-r3/source-inputs.json'
ORIGINAL_DIGEST = 'd947368432f3a27db24e901da758659274dc4b1fcce9ea5829c3a9a6a13998a7'


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate selection key: ' + key)
        result[key] = value
    return result


def read(path):
    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def identity(path):
    require(path.is_relative_to(ROOT), 'Input escapes selected root')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink input refused')
    require(stat.S_ISREG(path.stat().st_mode), 'Regular input required')
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def digest(rows):
    return hashlib.sha256(''.join(p + '\0' + r['sha256'] + '\n'
                                 for p, r in sorted(rows.items())).encode()).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def admit():
    selection = read(SELECTION)
    require(selection['schema'] == 1 and selection['id'] == 'android-inspection-diagnostic-r1470',
            'Unknown diagnostic selection')
    require(selection['entry'] == ENTRY and selection['bootstrap'] == BOOTSTRAP and
            selection['runner'] == RUNNER and selection['route'] == 'bootstrap.run_integration',
            'Diagnostic entry routing differs')
    require(selection['qualification'] is False and selection['historicalAdmissionTransferred'] is False,
            'Diagnostic selection cannot transfer qualification')
    require(selection['historical']['path'] == HISTORICAL and
            identity(ROOT / HISTORICAL) == selection['historical']['identity'],
            'Historical manifest metadata differs')
    historical = read(ROOT / HISTORICAL)
    require(len(historical) == 118 and digest(historical) == ORIGINAL_DIGEST,
            'Immutable original source118 differs')
    manifest_path = SELECTION.parent / 'source-inputs.json'
    require(identity(manifest_path) == selection['manifestIdentity'], 'Selected manifest bytes differ')
    selected = read(manifest_path)
    require(set(selected) == set(historical) | {ENTRY, BOOTSTRAP}, 'Diagnostic source roster differs')
    require(len(selected) == selection['sourceCount'] == 120 and
            digest(selected) == selection['sourceDigest'], 'Diagnostic source identity differs')
    require({p: r for p, r in selected.items() if p in historical and p != RUNNER} ==
            {p: r for p, r in historical.items() if p != RUNNER},
            'Diagnostic selection changed an original input beyond runner')
    require(selected[RUNNER] == {'bytes': 70163, 'sha256': '97d68e621d31352624375f0626433fba7b048282185221330a35025a2115b1dc'} and
            selected[BOOTSTRAP] == {'bytes': 18825, 'sha256': 'b1cab97748ee80a04446a39bf459160b1087c2c8a455a41b8095e62938bcf26c'},
            'Frozen diagnostic afterimages differ')
    for path, expected in selected.items():
        require(identity(ROOT / path) == expected, 'Selected input differs: ' + path)
    bootstrap = load('diagnostic_bootstrap_r1470', ROOT / BOOTSTRAP)
    authority = bootstrap.canonical()
    profile = authority.load_profile()
    actual = authority.source_inputs(profile)
    require(actual == {p: selected[p] for p in historical}, 'Actual runner owning inputs differ')
    require(bootstrap.RUNNER == ROOT / RUNNER and bootstrap.DRIVER == ROOT / authority.DRIVER,
            'Actual bootstrap routing differs')
    proof = {'id': selection['id'], 'source_count': len(selected), 'source_sha256': digest(selected),
             'runner_source_count': len(actual), 'runner_source_sha256': authority.source_digest(actual),
             'historical_source_count': 118, 'historical_source_sha256': ORIGINAL_DIGEST,
             'historicalAdmissionTransferred': False, 'qualification': False}
    return bootstrap, authority, proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('swift', 'swift-sdks', 'android-artifact', 'jdk', 'android-sdk', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--execute-toolchains', action='store_true')
    args = parser.parse_args()
    authority = None
    try:
        require(args.execute_toolchains, 'Explicit --execute-toolchains required')
        bootstrap, authority, proof = admit()
        tools = argparse.Namespace(**{key: value for key, value in vars(args).items()
                                      if key not in {'output', 'execute_toolchains'}})
        receipt = bootstrap.run_integration(authority, tools, dict(os.environ), args.output)
        receipt['diagnostic_source_selection'] = proof
        authority.save(args.output / 'receipt.json', receipt)
        print(json.dumps({'status': receipt['status'], 'error': receipt.get('error'),
                          'diagnostic_source_selection': proof}))
        return 0 if receipt['status'] == 'passed-java-crosscompile-only' else 1
    except Exception as error:
        print(json.dumps({'status': 'failed', 'error': str(error)}))
        return 1
    finally:
        if authority is not None:
            authority.command_exit_boundary()
            authority.cli_exit_boundary()


if __name__ == '__main__':
    sys.exit(main())
