#!/usr/bin/env python3
"""Read-only source/retained-artifact checks; executes no producer/product code."""
import hashlib
import json
import pathlib
import platform
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = pathlib.Path(__file__).resolve().parent
PROPOSAL = ROOT / 'verification/android-default-appearance-packaging-proposal'
EXPECTED = {
    'docs/android-default-appearance-packaging-proposal.md': '31f7983a5d5ecef5b90faeb540b28b4945e112d8821c6a550d57f89678c9f3b3',
    'verification/android-default-appearance-packaging-proposal/receipt.json': '68e5fff9d9647666b54ec385304ef2cab7ef79b3817bdf0d6989f8f0bbcba2a3',
    'verification/android-default-appearance-packaging-proposal/seal.sha256': '9170c192d00ebd1e30d2bdd8135c6f6d548990901cefd5960e0ffdc87646ef7f',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source_path(name):
    relative = pathlib.PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Unsafe manifest path')
    if name != 'docs/android-default-appearance-packaging-proposal.md' and not name.startswith('verification/android-default-appearance-packaging-proposal/'):
        raise ValueError('Unexpected proposal inventory input')
    return ROOT / name


def main():
    for name, expected in EXPECTED.items():
        assert digest(source_path(name).read_bytes()) == expected, name
    rows = (PROPOSAL / 'seal.sha256').read_text().splitlines()
    sealed = {}
    for row in rows:
        expected, name = row.split('  ', 1)
        assert name not in sealed, name
        assert digest(source_path(name).read_bytes()) == expected, name
        sealed[name] = expected
    receipt = json.loads((PROPOSAL / 'receipt.json').read_text())
    for name, record in receipt['files'].items():
        data = source_path(name).read_bytes()
        assert digest(data) == record['sha256'] and len(data) == record['bytes'], name
        assert sealed[name] == record['sha256'], name
    # Check the independently frozen baseline without modifying its sealed files.
    baseline_rows = (BASE / 'preaccess-seal.sha256').read_text().splitlines()
    for row in baseline_rows:
        expected, name = row.split('  ', 1)
        assert digest((ROOT / name).read_bytes()) == expected, name
    probe = json.loads((PROPOSAL / 'probe-2/receipt.json').read_text())
    for item in probe['commands']:
        assert digest((PROPOSAL / item['output']).read_bytes()) == item['output_sha256'], item['output']
    descriptor = (PROPOSAL / 'probe-2/descriptor.json').read_bytes()
    assert len(descriptor) == 9587
    assert digest(descriptor) == '1aeab75c457c21e5c801ab8b446490971d510021c945d0841252360becd8ead3'
    with zipfile.ZipFile(PROPOSAL / 'probe-2/asset-probe-unsigned.apk') as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), 'Duplicate synthetic ZIP names'
        assets = [name for name in names if name.startswith('assets/')]
        assert assets == ['assets/MixerAppearanceV2/descriptor.json'], assets
        assert archive.read(assets[0]) == descriptor
        contents = {name: digest(archive.read(name)) for name in names}
        assert contents == probe['synthetic_apk_entries']
    result = {
        'schema_version': 1,
        'status': 'source-and-retained-artifact-review-checks-passed',
        'command': [sys.executable, str(pathlib.Path(__file__).resolve())],
        'python': platform.python_version(),
        'checker_sha256': digest(pathlib.Path(__file__).read_bytes()),
        'frozen_proposal_bindings': EXPECTED,
        'proposal_seal_entries_verified': len(sealed),
        'proposal_receipt_entries_verified': len(receipt['files']),
        'independent_preaccess_seal_entries_verified': len(baseline_rows),
        'retained_command_output_bindings_verified': len(probe['commands']),
        'retained_synthetic_archive': {'complete_singleton_asset_inventory': True,
                                       'duplicate_zip_names': False,
                                       'asset_equals_retained_descriptor': True,
                                       'descriptor_bytes': len(descriptor),
                                       'descriptor_sha256': digest(descriptor)},
        'semantic_codec_validation_run_by_this_checker': False,
        'producer_or_product_code_executed': False,
        'compiler_or_native_runtime_commands': [],
        'scope': 'Frozen-input hash checks and retained synthetic ZIP read only. Not a fresh generated app, codec execution, cross-build or runtime acceptance.',
    }
    (BASE / 'frozen-proposal-checks.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({key: result[key] for key in ['status', 'proposal_seal_entries_verified',
                     'independent_preaccess_seal_entries_verified', 'producer_or_product_code_executed']}, sort_keys=True))


if __name__ == '__main__':
    main()
