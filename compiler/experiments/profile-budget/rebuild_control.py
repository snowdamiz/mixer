#!/usr/bin/env python3
"""Repeat the smallest candidate at identical compile paths, preserving first artifacts."""
import sys
sys.dont_write_bytecode = True
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('qualification_support', ROOT / 'compiler/qualification_support.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def identity(path):
    return {'path': os.path.relpath(path, ROOT), 'bytes': path.stat().st_size, 'sha256': helper.digest(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--receipt', type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt_path = args.receipt.resolve(strict=True)
    if HERE / 'evidence' not in receipt_path.parents:
        raise ValueError('receipt must be owned experiment evidence')
    prior = helper.strict_json(receipt_path.read_text())
    if not prior['status'].startswith('model-observations-matched-all-executable-variants'):
        raise ValueError('requires completed successful matrix')
    selected = next(value for value in prior['variants'] if value['name'] == prior['smallest_measured_variant'])
    build = next(value for value in prior['commands'] if value['name'] == selected['name'] + '-build')
    command = build['command']
    swift = prior['tools']['swift']
    if command[0] != swift['path'] or helper.tool_identity(swift['path']) != swift:
        raise ValueError('compiler identity differs')
    if helper.tool_identity(prior['tools']['node']['path']) != prior['tools']['node']:
        raise ValueError('Node identity differs')
    scratch = pathlib.Path(command[command.index('--scratch-path') + 1]).resolve(strict=True)
    package = pathlib.Path(command[command.index('--package-path') + 1]).resolve(strict=True)
    if HERE / 'local' not in scratch.parents or HERE / 'local' not in package.parents:
        raise ValueError('control must stay inside owned local outputs')
    artifact = ROOT / selected['artifact']['path']
    if identity(artifact) != selected['artifact']:
        raise ValueError('first artifact identity differs')
    for value in prior['source_inputs'].values():
        if identity(ROOT / value['path']) != value:
            raise ValueError('source input identity differs')
    source_hashes = helper.strict_json((receipt_path.parent / 'fieldlog-source-manifest.json').read_text())
    if any(helper.digest(package / 'fieldlog' / name) != digest for name, digest in source_hashes.items()):
        raise ValueError('frozen model sources differ')
    evidence = receipt_path.parent / 'rebuild-control'
    evidence.mkdir(exist_ok=False)
    output = scratch.parent / 'rebuild-control'
    output.mkdir(exist_ok=False)
    commands = []
    env = helper.clean_environment()
    env['DEVELOPER_DIR'] = prior['environment']['DEVELOPER_DIR']
    recorder = helper.CommandRecorder(evidence, commands, ROOT)
    result = {'schema_version': 1, 'status': 'running', 'commands': commands,
        'scope': 'same-path clean compiler/linker rebuild and full established model observation comparison',
        'matrix_receipt': identity(receipt_path), 'first_artifact': selected['artifact'],
        'owned_vm_execution_qualified': False, 'device_or_ota_qualified': False,
        'timing_scope': 'Mac development command wall time only',
        'implementation_agent_selection': {'model': 'gpt-6.1-sol', 'reasoning_effort': 'xhigh'},
        'independent_review': False}
    backup = scratch.with_name(scratch.name + '.first-build')
    control = scratch.with_name(scratch.name + '.control-build')
    if backup.exists() or control.exists():
        raise ValueError('control paths already exist')
    link_outputs = []
    for key in ['--Map=', '--why-extract=']:
        value = next(value for value in command if value.startswith(key))
        original = pathlib.Path(value[len(key):]).resolve(strict=True)
        if scratch.parent not in original.parents:
            raise ValueError('linker output escapes owned experiment directory')
        copy = output / original.name
        shutil.copyfile(original, copy)
        link_outputs.append((original, copy, helper.digest(original)))
    try:
        # Move only owned build temporaries. Restore first artifacts and map files
        # even if compilation fails; keep the control build at a separate path.
        scratch.rename(backup)
        try:
            recorder.run('same-path-clean-build', command, env=env, timeout=300)
        finally:
            if scratch.exists():
                scratch.rename(control)
            backup.rename(scratch)
            for original, copy, digest in link_outputs:
                shutil.copyfile(copy, original)
                if helper.digest(original) != digest:
                    raise ValueError('failed to restore first linker evidence')
        rebuilt = control / artifact.relative_to(scratch)
        result['rebuilt_artifact'] = identity(rebuilt)
        result['bit_identical_same_path_rebuild'] = helper.digest(rebuilt) == selected['artifact']['sha256']
        compressed = gzip.compress(rebuilt.read_bytes(), compresslevel=9, mtime=0)
        compressed_path = output / 'rebuilt.wasm.gz'
        compressed_path.write_bytes(compressed)
        result['rebuilt_gzip9_mtime0'] = identity(compressed_path)
        result['gzip_identical'] = result['rebuilt_gzip9_mtime0']['sha256'] == selected['gzip9_mtime0']['sha256']
        observations = helper.model_observations(helper.strict_json(recorder.run('rebuilt-oracle',
            [prior['tools']['node']['path'], '--no-warnings', HERE / 'oracle.mjs', rebuilt], env=env)))
        if observations != prior['expected_model_observations']:
            raise ValueError('rebuilt model observations differ')
        result['observations'] = observations
        result['first_artifact_restored'] = identity(artifact) == selected['artifact']
        if not result['first_artifact_restored']:
            raise ValueError('first artifact changed')
        result['source_manifest'] = {str(path.relative_to(ROOT)): helper.digest(path) for path in
            [pathlib.Path(__file__), HERE / 'oracle.mjs', ROOT / 'compiler/qualification_support.py']}
        result['status'] = 'completed; full established model observations matched'
        result['limitation'] = 'Same-path result does not assert path-independent compiler reproducibility; differing absolute roots changed two app .swift_modhash entries in earlier diagnostic runs.'
    except Exception as error:
        result['status'] = 'failed'
        result['failure'] = str(error)
        raise
    finally:
        (evidence / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
