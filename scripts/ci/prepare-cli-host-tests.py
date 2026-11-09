#!/usr/bin/env python3
"""Prepare one private, job-scoped CLI host test environment without launching tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(receipt_path, output):
    receipt = json.loads(Path(receipt_path).read_text())
    if receipt.get('status') != 'verified-installed-toolchain':
        raise ValueError('verified Apple toolchain receipt required')
    developer = Path(receipt['developerDirectory']).resolve(strict=True)
    swift = Path(receipt['swiftPath'])
    if not swift.is_absolute() or not swift.resolve(strict=True).is_relative_to(developer):
        raise ValueError('selected Swift must belong to the verified developer directory')
    swiftc = swift.parent / 'swiftc'
    frontend = swift.parent / 'swift-frontend'
    for path, expected in ((swift, receipt['swiftSHA256']), (swiftc, receipt['swiftSHA256']),
                           (frontend, receipt['swiftFrontendSHA256'])):
        if not path.resolve(strict=True).is_relative_to(developer) or not os.access(path, os.X_OK) or digest(path) != expected:
            raise ValueError('selected compiler identity drift: ' + str(path))
    output = Path(output)
    if not output.is_absolute() or output != output.resolve() or any(c in str(output) for c in '\n\r\0'):
        raise ValueError('absolute canonical output directory required')
    # A fresh root prevents concurrent jobs and repeated attempts from sharing receipts.
    output.mkdir(mode=0o700)
    for name in ('bin', 'tmp', 'store-children'):
        (output / name).mkdir(mode=0o700)
    launcher = output / 'bin/swift'
    # dup2 precedes exec: exact compiler bytes and status, in one kernel stream order.
    selected_driver = shlex.quote(str(swift))
    launcher.write_text('#!/bin/sh\nif [ "$#" -eq 1 ] && [ "$1" = "--version" ]; then\n'
                        + '  exec ' + selected_driver + ' "$@" 2>&1\nfi\n'
                        + 'exec ' + selected_driver + ' "$@"\n')
    launcher.chmod(0o700)
    selected = {'PATH': str(output / 'bin') + ':' + str(swift.parent) + ':' + os.environ.get('PATH', '/usr/bin:/bin'),
                'SWIFT_EXEC': str(swiftc), 'TMPDIR': str(output / 'tmp') + '/',
                'MIXER_STORE_CUSTODY_DIR': str(output / 'store-children'),
                'MIXER_SUITE_HOLD': str(output / 'SUITE-HOLD.json')}
    (output / 'environment.sh').write_text(''.join('export ' + key + '=' + shlex.quote(value) + '\n' for key, value in selected.items()))
    result = {'schema': 1, 'toolchainReceiptSHA256': digest(Path(receipt_path)),
              'swiftPath': str(swift), 'swiftSHA256': digest(swift),
              'swiftcPath': str(swiftc), 'swiftcSHA256': digest(swiftc),
              'swiftFrontendSHA256': digest(frontend), 'launcherSHA256': digest(launcher),
              'output': str(output), 'environment': selected,
              'scope': 'CLI host tests only; exact compiler bytes, no identity normalization'}
    (output / 'selection.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--toolchain-receipt', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.toolchain_receipt, args.output), indent=2))


if __name__ == '__main__':
    main()
