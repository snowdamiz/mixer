#!/usr/bin/env python3
"""One bounded ordinary-CI artifact DATA review; no historical main/wrapper runs."""
import argparse
import ast
import ctypes
import _ctypes
import _strptime
import _thread
import datetime
import encodings.cp437
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import platform
import posix
import re
import selectors
import shutil
import signal
import _signal
import socket
import _socket
import stat
import struct
import subprocess
import _posixsubprocess
import sys
import threading
import time
import uuid
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
PREP = ROOT / 'verification/rust-1991-actual-audit-preparation-v2'
EXTRACTED = Path('/tmp/mixer-20261107-ci-df7-envelope')
ARCHIVE = Path('/tmp/mixer-20261107-ci-df7-envelope.zip')
REVISION = 'df7b67ace3441707049d47c289cefaed83dcdc6c'
GIT_TREE = 'c78ef17a48852e31f70da4dbf9b84a11926164fa'
ZIP_SHA = '9a837ebd67d865b2bc4f5cc7e53f6e245ecdd1b49731f2be49e68279384890af'
WORKFLOW_SHA = '5cc067d90adaadbb4741e8e0e25bf1ecace4fa2d5ce87cbe13cfddb92fc67325'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def trusted_module(name, path, digest):
    assert sha(path.read_bytes()) == digest, str(path)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

assert sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode
assert not (OUT / 'data-audit.json').exists(), 'One fresh review invocation only'
guard = trusted_module('fresh_envelope_guard', PREP / 'deny_runtime.py',
    '69873787132f3c8d8f29977c87101e5c3d0337ae8429104bb49f1658b102cb74')
guard.install(OUT)
a = trusted_module('fresh_envelope_auditor', PREP / 'audit_actual.py',
    '6ab801562475b4cca7a5ca496b49758184b956caf1d868a79932fc8a4197dfd8')

started = time.monotonic()
read_rows = {}

def observe(path):
    data = a.raw(path)
    row = {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}
    previous = read_rows.setdefault(str(path), row)
    a.need(previous == row, 'Observed input stable: ' + str(path))
    return data

def write(name, value):
    (OUT / name).write_bytes(a.report_bytes(value))

result = {
    'schema': 1, 'scope': 'fresh ordinary CI envelope artifact data audit only',
    'run_id_root_attribution': 42419571138, 'artifact_id_root_attribution': 13592908052,
    'revision': REVISION, 'git_tree': GIT_TREE, 'archive_sha256': ZIP_SHA,
    'artifact_data_checks_passed': False, 'full_acceptance': False,
    'general_compiler_api_cache_or_ga_qualification': False,
    'historical_selected_invocation_replayed': False,
    'historical_attempt_budget': {'selected': 1, 'consumed': 1, 'remaining': 0},
    'command': [sys.executable, '-I', '-B', '-S', str(Path(__file__).resolve())],
    'python': {'executable': sys.executable, 'version': sys.version},
    'external_transport_eof_lease_invalidation_provider_disposal_proven': False,
    'recorded_custody_is_independent_kernel_trace': False,
    'historical_auditor_main_binding_source_closure_unpack_invoked': False,
}
try:
    # Bind the reviewed validator implementation and every executable dependency.
    own = a.load(PREP / 'preparation-seal.json')
    a.need(sha(observe(PREP / 'preparation-seal.json')) ==
        '26051a74891b420c487b6262b865ab5ecf3160a3989a14cc34acf4c4dd439213', 'Prepared auditor seal')
    a.rows_verify(PREP, own['members'])
    for row in own['members']:
        observe(PREP / row['path'])
    provenance = []
    bindings = a.load(PREP / 'source-bindings.json')
    for row in bindings['members']:
        path = ROOT / row['path']
        if not path.exists():
            a.need(row['path'] == 'verification/envelope-ordinary-actual-review/raw/audit_body.py',
                   'No unexpected missing source')
            provenance.append({'path': row['path'], 'missing': True, 'used_by_current_validator': False})
            continue
        data = observe(path)
        if sha(data) != row['sha256'] or len(data) != row['bytes']:
            a.need(row['path'] == '.github/workflows/verify.yml' and sha(data) == WORKFLOW_SHA,
                   'No unexplained source drift')
            provenance.append({'path': row['path'], 'historical_sha256': row['sha256'],
                               'actual_sha256': sha(data), 'swift_job_checked_separately': True})
    preserved = a.load(PREP / 'preservation-bindings.json')
    a.rows_verify(ROOT, preserved['members'])
    for row in preserved['members']:
        observe(ROOT / row['path'])
    for directory, manifest, count in [(ROOT / a.ADOPTION, 'seal.json', 19),
                                      (ROOT, a.ADOPTION + '/dependencies.json', 111)]:
        packet = a.load(directory / manifest)
        a.need(len(packet['members']) == count and a.tree(packet['members']) == packet['tree_sha256'],
               'Executable closure count/tree')
        a.rows_verify(directory, packet['members'])
        for row in packet['members']:
            observe(directory / row['path'])
    workflow = observe(ROOT / '.github/workflows/verify.yml').decode()
    job = re.search(r'^  swift:\n.*?(?=^  [A-Za-z0-9_-]+:\n|\Z)', workflow, re.M | re.S)
    a.need(job is not None and job.group().encode() == observe(ROOT / a.ADOPTION / 'workflow/swift-job.yml'),
           'Current installed Swift job equals sealed job exactly')
    defs = []
    for relative in (a.POLICY, a.RUNNER):
        source = observe(ROOT / relative).decode()
        defs.append({n.name: ast.get_source_segment(source, n) for n in ast.parse(source).body
                     if isinstance(n, ast.FunctionDef)})
    for name in ('rustc_identity', 'select_compiler', 'select_host_target'):
        a.need(defs[0][name] == defs[1][name], 'Original policy definition unchanged: ' + name)
    for name in ('refusal-receipt.json', 'root-binding.json', 'seal.json', 'actual-audit-observation.json'):
        observe(ROOT / 'verification/rust-1991-first-actual-result' / name)
    root_receipt = observe(ROOT / 'verification/plan-continuation-2026-11-07/envelope-ci-artifact.json')
    result['root_artifact_receipt'] = json.loads(root_receipt)
    result['prior_source_closure_differences'] = provenance
    result['exact_envelope_executable_dependencies_and_swift_job'] = True

    # Mirror the reviewed bounded ZIP admission, without its extraction/writes.
    blob = a.raw(ARCHIVE, a.BOUNDS['archive_bytes'])
    a.need(len(blob) == 770713 and sha(blob) == ZIP_SHA, 'Exact actual archive')
    fixed = a.fixed_archive_files()
    files, directories, payloads, normalized = {}, set(), {}, set()
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        infos = archive.infolist()
        a.need(0 < len(infos) <= a.BOUNDS['members'], 'ZIP member count')
        a.need(sum(i.file_size for i in infos) <= a.BOUNDS['expanded_archive_bytes'], 'Expanded ZIP bound')
        for info in infos:
            name, is_dir = a.zip_member_name(info, blob)
            a.need(name not in normalized, 'Unique original ZIP names')
            normalized.add(name)
            mode = stat.S_IFMT(info.external_attr >> 16)
            a.need(mode in ({0, stat.S_IFDIR} if is_dir else {0, stat.S_IFREG}) and not info.flag_bits & 1
                   and info.compress_type in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
                   and 0 <= info.file_size <= a.BOUNDS['member_bytes'], 'Regular bounded ZIP entry')
            if is_dir:
                directories.add(name)
            else:
                a.need(name in fixed or name.startswith('_temp/analyzer-envelope/retained/'), 'Selected path')
                files[name] = info
        a.need(not any(p.as_posix() in files for name in files for p in Path(name).parents
                       if p.as_posix() != '.'), 'No ancestor collision')
        retention_name = '_temp/analyzer-envelope/retention.json'
        a.need(retention_name in files and files[retention_name].file_size <= a.JSON_LIMITS['raw_bytes'],
               'Bounded retention roster')
        a.early_archive_closure(files, directories, fixed, a.strict(archive.read(files[retention_name])))
        for info in infos:
            data = archive.read(info)
            a.need(len(data) == info.file_size and (not info.is_dir() or not data), 'ZIP length/CRC')
            if not info.is_dir():
                name = info.orig_filename
                a.need(a.raw(EXTRACTED / a.canonical(name)) == data, 'Extracted file equals ZIP: ' + name)
                payloads[name] = data
    actual_files = set()
    for directory, dirs, names in os.walk(EXTRACTED, followlinks=False):
        a.need(len(actual_files) <= 1000, 'Bounded extracted file walk')
        for name in dirs + names:
            p = Path(directory) / name
            a.need(not p.is_symlink(), 'No extracted symlink')
        actual_files.update((Path(directory) / n).relative_to(EXTRACTED).as_posix() for n in names)
    a.need(actual_files == set(payloads), 'Exact extracted closure')
    result.update(a.verify_payloads(payloads, directories, EXTRACTED,
                                   {'revision': REVISION, 'git_tree': GIT_TREE}))
    result['artifact_data_checks_passed'] = True
    result['archive_expanded_bytes'] = sum(map(len, payloads.values()))
    result['archive_manifest'] = 'archive-manifest.json'
    write('archive-manifest.json', [{'path': n, 'bytes': len(b), 'sha256': sha(b)}
                                   for n, b in sorted(payloads.items())])
    # Freeze only receipt/sidecars/output/log metadata, never the 64 MB payload set.
    compact_bytes = 0
    for name, data in sorted(payloads.items()):
        fixture = name.startswith('_temp/analyzer-envelope/')
        relative = name.removeprefix('_temp/analyzer-envelope/')
        selected = fixture and (relative in {'receipt.json', 'adapter-start.json', 'adapter-result.json',
                                             'retention.json', 'output-ownership.json'} or relative.startswith('commands/'))
        selected |= name.startswith('mixer/mixer/' + a.ADOPTION + '/logs/')
        if selected:
            compact_bytes += len(data)
            a.need(compact_bytes <= 2 * 1024 * 1024, 'Compact frozen record bound')
            target = OUT / 'records' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    result['compact_frozen_record_bytes'] = compact_bytes
    r = a.load(EXTRACTED / '_temp/analyzer-envelope/receipt.json')
    result['compiler'] = r['rustc']
    result['bounds_observed'] = {'active_seconds': r['active_elapsed_seconds'],
        'total_seconds': r['elapsed_seconds'], 'active_limit': 480, 'cleanup_limit': 60,
        'compiler_limit': 60, 'test_group_limit': 120, 'per_stream_bytes': 8388608,
        'all_streams_bytes': 67108864}
    result['recorded_controls'] = {'passed': 33, 'failed': 0, 'skipped': 0,
        'validation': 'Exact recorded names, terminal ok lines, counts, source bindings and guard/cleanup records checked'}
    result['reap_evidence'] = '40 command rows bind child PID to owned PGID, direct return, exit, group absence and separate stream EOF; pinned runner records these after proc.wait(timeout=5). No local process probe.'
    for name, data in payloads.items():
        a.need(a.raw(EXTRACTED / name) == data, 'Artifact extracted input stable after audit')
    a.need(a.raw(ARCHIVE, a.BOUNDS['archive_bytes']) == blob, 'ZIP stable after audit')
except BaseException as error:
    result['failure'] = {'type': type(error).__name__, 'message': str(error)[:1024]}
finally:
    try:
        for row in list(read_rows.values()):
            observe(Path(row['path']))
        a.need(guard.DENIED == [], 'No denied runtime/write attempts')
        result['read_sources_stable_after_audit'] = True
    except BaseException as error:
        result['artifact_data_checks_passed'] = False
        result['postflight_failure'] = {'type': type(error).__name__, 'message': str(error)[:1024]}
    result['checks'] = a.CHECKS
    result['json_budget_used'] = a.JSON_USED
    result['guard_denials'] = guard.DENIED
    result['elapsed_data_audit_seconds'] = time.monotonic() - started
    write('input-manifest.json', sorted(read_rows.values(), key=lambda r: r['path']))
    write('data-audit.json', result)
    print(json.dumps({k: result.get(k) for k in ('artifact_data_checks_passed', 'failure', 'postflight_failure',
                                              'checks', 'guard_denials', 'elapsed_data_audit_seconds')}))
sys.exit(0 if result['artifact_data_checks_passed'] else 1)
