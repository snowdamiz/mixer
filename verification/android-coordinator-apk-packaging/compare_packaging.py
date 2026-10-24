#!/usr/bin/env python3
"""Retain actual ZIP metadata for the original, rejected, and repackaged APKs."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('packaging_comparison_validator', HERE / 'apk_packaging.py')
guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
INPUTS = {
    'original-candidate2': ('verification/android-coordinator-join/candidate-2',
        '642962760271300298db98efd9f2018c159a2e9767843e4ef2bad84d9f824459',
        '396466de00b4b905c664632e711a5dcda151f85af1a4f9e47c6ff1b68e5c276c'),
    'rejected-click-candidate1': ('verification/android-coordinator-click-fixture/candidate-1',
        'feaa639b8b719492c5889222246cb62ebd4e9dd807379ccd984c5062f60660a4',
        '9b87cd52a1f0eaa82ac23c7bd26c22b1c116cf54d782aac1e7ec0fd5e6924b63'),
    'packaging-candidate1': ('verification/android-coordinator-apk-packaging/candidate-1',
        '7305ff2bd05843ea26b7e82429767416ec219ec35e0587d4bcdc273204b9f4de',
        '78af8c5df197fb6f163f3010825648a1b1a50427c9ab963b1c5aeca1e513b3ba'),
}


def compare():
    result = {}
    for label, (relative, archive_sha, apk_sha) in INPUTS.items():
        archive_path = ROOT / relative / 'built-artifacts.tar.gz'
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != archive_sha:
            raise ValueError('comparison bound archive drift: ' + label)
        with tarfile.open(archive_path, 'r:gz') as archive:
            data = archive.extractfile('coordinator-join.apk').read()
        if hashlib.sha256(data).hexdigest() != apk_sha:
            raise ValueError('comparison bound APK drift: ' + label)
        entries = {}
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for info in archive.infolist():
                h = struct.unpack_from('<IHHHHHIIIHH', data, info.header_offset)
                offset = info.header_offset + 30 + h[-2] + h[-1]
                entries[info.filename] = {'compressionMethod': info.compress_type,
                    'localHeaderMethod': h[3], 'localHeaderOffset': info.header_offset,
                    'localDataOffset': offset, 'localDataOffsetMod4': offset % 4,
                    'localDataOffsetMod16384': offset % 16384, 'bytes': info.file_size,
                    'sha256': hashlib.sha256(archive.read(info)).hexdigest()}
        try:
            checked = guard.validate(data)
            validation = {'status': checked['status']}
        except ValueError as failure:
            validation = {'status': 'rejected', 'failure': str(failure)}
        result[label] = {'archivePath': str(archive_path.relative_to(ROOT)), 'archiveSHA256': archive_sha,
            'apkSHA256': apk_sha, 'entries': entries, 'actualPackagingValidator': validation}
    if result['rejected-click-candidate1']['actualPackagingValidator']['status'] != 'rejected':
        raise ValueError('known rejected compressed-resource APK unexpectedly accepted')
    if any(result[name]['actualPackagingValidator']['status'] == 'rejected'
           for name in ('original-candidate2', 'packaging-candidate1')):
        raise ValueError('valid original/repackaged APK packaging rejected')
    return {'status': 'passed-actual-ZIP-packaging-comparison', 'APKs': result,
        'nativeCommandsExecuted': 0, 'nativeInstancesStarted': 0, 'physicalTargetsQueried': False,
        'scope': 'ZIP/ELF packaging observations only; installation/app assertions remain pending'}


if __name__ == '__main__':
    print(json.dumps(compare(), indent=2, sort_keys=True))
