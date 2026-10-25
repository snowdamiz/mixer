#!/usr/bin/env python3
"""Freeze or verify the source/host/compile handoff with file reads only."""
import argparse
import datetime
import json
from pathlib import Path
import sys
import tarfile

import prepare


def observed():
    verified = prepare.verify()
    host = json.loads((prepare.BASE / 'host-receipt.json').read_bytes())
    compile_base = prepare.BASE / 'compile-attempt-1'
    compiled = json.loads((compile_base / 'receipt.json').read_bytes())
    prepare.require(host['passed'] is True and (host['testsRun'], host['failures'], host['errors'], host['skipped']) == (26, 0, 0, 0),
                    'Exact passing host controls required')
    prepare.require(host['preparedSHA256'] == compiled['preparedSHA256'] == verified['preparedSHA256']
                    and compiled['sourceTreeSHA256'] == verified['sourceTreeSHA256'], 'Source identity changed')
    prepare.require(all(prepare.row(prepare.BASE / name) == row for name, row in host['ownedSources'].items()), 'Tested source changed')
    prepare.require(compiled['status'] == 'compiled-generic-simulator-only' and all(value == 0 for value in compiled['exitCodes'].values()),
                    'Successful compile-only receipt required')
    prepare.require(compiled['cleanup']['scratchAbsent'] is True and not (compile_base / 'scratch').exists()
                    and compiled['cleanup']['ownedCompilerGroupsAbsent'] is True, 'Compile cleanup incomplete')
    product_manifest = json.loads((compile_base / 'product-manifest.json').read_bytes())
    archive = compile_base / 'products.tar.gz'
    prepare.require(prepare.row(archive) == compiled['productArchive'] == product_manifest['archive'], 'Product archive changed')
    actual = {}
    with tarfile.open(archive, 'r:gz') as source:
        seen = set()
        for member in source:
            prepare.require(member.name not in seen and not Path(member.name).is_absolute() and '..' not in Path(member.name).parts,
                            'Unsafe compiled member')
            seen.add(member.name)
            if member.isdir(): continue
            if member.issym(): actual[member.name] = {'kind': 'symlink', 'mode': member.mode, 'target': member.linkname}
            else:
                prepare.require(member.isfile(), 'Unexpected compiled member kind')
                data = source.extractfile(member).read()
                actual[member.name] = {'kind': 'file', 'bytes': len(data), 'mode': member.mode, 'sha256': prepare.sha(data)}
    prepare.require(actual == product_manifest['products'] and prepare.sha(prepare.stable(actual)) == compiled['productTreeSHA256'],
                    'Complete compiled product bytes differ')
    paths = [path for path in sorted(prepare.BASE.rglob('*')) if path.is_file() and path.name != 'handoff.json']
    paths.append(prepare.ROOT / 'docs/apple-focus-reference-diagnostic-v1.md')
    members = {str(path.relative_to(prepare.ROOT)): prepare.row(path) for path in paths}
    return verified, host, compiled, members


def main(action):
    verified, host, compiled, members = observed()
    path = prepare.BASE / 'handoff.json'
    if action == 'freeze':
        prepare.require(not path.exists(), 'Preserve frozen handoff')
        receipt = {'schema': 'mixer.apple-focus-reference-frozen-handoff.1', 'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'command': [sys.executable, '-B', str(prepare.BASE / 'freeze.py'), 'freeze'], 'cwd': str(prepare.ROOT), 'python': sys.version,
            'sourceRevisionLabel': compiled['sourceRevisionLabel'], **verified,
            'originalPacketSHA256': prepare.PACKET_SHA, 'originalFailurePreserved': True,
            'members': members, 'memberTreeSHA256': prepare.sha(prepare.stable(members)), 'testsRun': host['testsRun'],
            'productArchiveSHA256': compiled['productArchive']['sha256'], 'productTreeSHA256': compiled['productTreeSHA256'],
            'compileExitCodes': compiled['exitCodes'], 'cleanup': compiled['cleanup'],
            'scope': 'Frozen source derivative, host controls and generic simulator compilation only; root review before fresh runtime assembly.',
            'nativeExecuted': False, 'runtimeSelected': False, 'runnablePacketAssembled': False, 'servicesStarted': 0,
            'explicitSimulatorOrDeviceCommands': 0, 'uiOrCapturePerformed': False, 'gitMutationPerformed': False,
            'completeCaseSet': False, 'runPassed': False, 'fullSixCaseQualification': False, 'gaAccepted': False,
            'physicalPhones': 'disconnected-deferred'}
        path.write_bytes(prepare.stable(receipt))
    else:
        receipt = json.loads(path.read_bytes())
        prepare.require(receipt['members'] == members and receipt['memberTreeSHA256'] == prepare.sha(prepare.stable(members)),
                        'Frozen handoff members changed')
        prepare.require(receipt['preparedSHA256'] == verified['preparedSHA256'] and receipt['productTreeSHA256'] == compiled['productTreeSHA256'],
                        'Frozen handoff identities changed')
    print(json.dumps({'passed': True, 'handoffSHA256': prepare.row(path)['sha256'], 'members': len(members), **verified}, sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze', 'verify'])
    main(parser.parse_args().action)
