#!/usr/bin/env python3
"""Offline source and initial-archive audit; launches no process or socket."""
from pathlib import Path
import hashlib
import importlib.util
import io
import json
import sys
import tarfile
from unittest import mock

sys.dont_write_bytecode = True
root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
path = root / 'hosted/scripts/test-identity-network.py'
spec = importlib.util.spec_from_file_location('identity_transfer_source_audit', path)
subject = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = subject
with mock.patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), mock.patch('os.system', side_effect=AssertionError('shell forbidden')), mock.patch('socket.socket', side_effect=AssertionError('socket forbidden')), mock.patch('socket.create_connection', side_effect=AssertionError('connection forbidden')):
    spec.loader.exec_module(subject)
    product = {name: (root / name).read_bytes() for name in subject.FROZEN_MANIFEST}
    observed = {name: {'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()} for name, body in product.items()}
    subject.validate_source_manifest(observed)
    helpers = {'collector-prerequisites.exs': subject.PREREQUISITES_EXS.encode(), 'collector-bootstrap.exs': subject.BOOTSTRAP_EXS.encode(), 'collector-manifest.exs': subject.MANIFEST_EXS.encode(), 'collector-netns.exs': subject.NETNS_EXS.encode(), 'collector-observer.exs': subject.OBSERVER_EXS.encode(), 'frozen-manifest.json': json.dumps(subject.FROZEN_MANIFEST, sort_keys=True, separators=(',', ':')).encode()}
    data = subject.source_tar({**product, **helpers})
    subject.validate_transfer_archive(data)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        members = archive.getmembers()
    result = {'scope': 'offline file/hash/initial-archive audit only; no Docker/native runtime/child/socket', 'product_files': len(observed), 'product_tree_digest_sha256': subject.canonical_digest(observed), 'initial_archive': {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'members': len(members), 'uid_values': sorted({member.uid for member in members}), 'gid_values': sorted({member.gid for member in members}), 'mode_values_octal': sorted({oct(member.mode) for member in members}), 'plain_regular_only': all(member.type == tarfile.REGTYPE and member.sparse is None and member.offset_data == member.offset + 512 for member in members), 'pax_headers_absent': all(not member.pax_headers for member in members)}}
    assert result['initial_archive']['bytes'] == 3993600
    assert result['initial_archive']['sha256'] == '14c1b38284fb835a16841b8dcb1065b2ef600abd6d59d2e8d869be561204b9fd'
    (out / 'source-audit.json').write_text(json.dumps(result, sort_keys=True, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))
