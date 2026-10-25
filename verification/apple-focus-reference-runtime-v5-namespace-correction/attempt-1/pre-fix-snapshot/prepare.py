#!/usr/bin/env python3
"""Narrow V5 output-prefix derivative. Native dispatch is a separate root action."""
import argparse
import contextlib
import datetime
import difflib
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile
import types

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ORIGINAL = ROOT / 'verification/apple-focus-reference-runtime-v5'
REVIEW = ROOT / 'verification/apple-focus-reference-runtime-v5-independent-review'
HANDOFF = '3d22fa59106d6bc6c585ed53d720b31f1bbe50f8e811cf528758b274918ac02b'
REVIEW_HANDOFF = 'de3a06f28e3e8cc2b1ee0773c50f3181331e5ae05518de60f79a57b33f22c156'
ORIGINAL_PACKET = '86c7d9604c11349fcf46fb35117130f7262f87acb54da533205a32dfc54ae7ac'
PRODUCT = '0941185e39cc0171b0bf5d2aeb72738588e88b9c7b3d676f893b70c3bf644fa8'
PRODUCT_PREFIX = 'verification/apple-focus-reference-diagnostic-v1/compile-attempt-1/'
V1 = None  # Bound only within dispatch(), from the immutable V5 input archive.
OLD_PREFIX = b"'native-run-v4-'+_ROOT['runID']"
NEW_PREFIX = b"'native-run-v5-'+_ROOT['runID']"
SOURCES = ['prepare.py', 'run_controls.py', 'freeze.py']
ARTIFACTS = ['adapter.py', 'importer.py', 'runtime-source-manifest.json',
             'runtime-sources.tar.gz', 'selection-template.json', 'correction.patch']


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()


def row(path):
    info = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
            'Canonical single-link regular file required: ' + str(path))
    raw = path.read_bytes()
    return {'kind': 'file', 'mode': stat.S_IMODE(info.st_mode), 'bytes': len(raw), 'sha256': sha(raw)}


def safe_name(name):
    path = PurePosixPath(name)
    require(type(name) is str and name and not path.is_absolute() and '..' not in path.parts
            and str(path) == name, 'Canonical relative archive path required')
    return path


def manifest(payload):
    return {name: {'kind': 'file', 'mode': 0o644, 'bytes': len(raw), 'sha256': sha(raw)}
            for name, raw in sorted(payload.items())}


def archive_payload(path, rows, expected_sha, prefix=''):
    require(row(path)['sha256'] == expected_sha, 'Archive SHA-256 changed: ' + str(path))
    expected_dirs = {prefix.rstrip('/')} if prefix else set()
    for name in rows:
        safe_name(name)
        expected_dirs.update(str(parent) for parent in PurePosixPath(prefix + name).parents
                             if str(parent) != '.')
    payload, directories, seen = {}, set(), set()
    with tarfile.open(path, 'r:gz') as archive:
        for member in archive.getmembers():
            name = member.name
            safe_name(name)
            require(name not in seen, 'Duplicate archive member')
            seen.add(name)
            if member.isdir():
                require(member.mode == 0o755, 'Archive directory mode differs')
                directories.add(name)
                continue
            require(member.isfile() and name.startswith(prefix), 'Unexpected archive member type/path')
            relative = name[len(prefix):]
            require(relative in rows, 'Unlisted archive file: ' + relative)
            raw = archive.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)} == rows[relative],
                    'Archive file differs: ' + relative)
            payload[relative] = raw
    require(set(payload) == set(rows) and directories == expected_dirs, 'Exact archive inventory required')
    return payload


def tree(path):
    require(path.resolve() == path and path.is_dir() and not path.is_symlink()
            and stat.S_IMODE(path.stat().st_mode) == 0o755, 'Canonical product/source root required')
    rows, directories = {}, set()
    for item in sorted(path.rglob('*')):
        require(not item.is_symlink(), 'Archive tree redirection refused')
        if item.is_file():
            rows[str(item.relative_to(path))] = row(item)
        else:
            require(item.is_dir() and stat.S_IMODE(item.stat().st_mode) == 0o755, 'Unexpected tree directory')
            directories.add(str(item.relative_to(path)))
    implied = {str(parent) for name in rows for parent in PurePosixPath(name).parents if str(parent) != '.'}
    require(directories == implied, 'Tree directory inventory differs')
    return rows


def materialize(destination, rows, payload):
    require(not destination.exists() and not destination.is_symlink()
            and destination.resolve() == destination, 'Fresh canonical materialization required')
    require(set(rows) == set(payload), 'Materialization inventory differs')
    destination.mkdir(mode=0o755)
    for name, expected in sorted(rows.items()):
        safe_name(name)
        raw = payload[name]
        require(expected['kind'] == 'file' and len(raw) == expected['bytes'] and sha(raw) == expected['sha256'],
                'Materialization bytes differ: ' + name)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        for directory in [path.parent, *path.parent.parents]:
            if directory == destination.parent:
                break
            directory.chmod(0o755)
        with path.open('xb') as stream:
            stream.write(raw)
        path.chmod(expected['mode'])
    require(tree(destination) == rows, 'Materialization changed bytes/modes')


def archive_sources(path, source, rows):
    require(tree(source) == rows and not path.exists(), 'Exact fresh archive source required')
    directories = {'selected'} | {str(parent) for name in rows
                                  for parent in PurePosixPath('selected/' + name).parents if str(parent) != '.'}
    with path.open('xb') as target, gzip.GzipFile(fileobj=target, mode='wb', filename='', mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode='w', format=tarfile.PAX_FORMAT) as archive:
            for name in sorted(directories):
                info = tarfile.TarInfo(name); info.type = tarfile.DIRTYPE; info.mode = 0o755
                archive.addfile(info)
            for name, expected in sorted(rows.items()):
                raw = (source / name).read_bytes()
                info = tarfile.TarInfo('selected/' + name); info.mode = expected['mode']; info.size = len(raw)
                archive.addfile(info, io.BytesIO(raw))
    result = {'schema': 1, 'scope': 'V5-001 selected runtime prefix correction only',
              'files': rows, 'treeSHA256': sha(stable(rows)), 'archive': row(path),
              'directories': sorted(directories), 'directoryMode': 0o755}
    require(archive_payload(path, rows, result['archive']['sha256'], 'selected/')
            == {name: (source / name).read_bytes() for name in rows}, 'Archive round-trip differs')
    return result


def helpers():
    # Independent stdlib archive utilities. No historical producer helper imports.
    return types.SimpleNamespace(archive_payload=archive_payload, materialize=materialize,
                                 tree=tree, archive_sources=archive_sources)


def references():
    require(row(ORIGINAL / 'handoff.json')['sha256'] == HANDOFF, 'Frozen V5 handoff changed')
    require(row(REVIEW / 'handoff.json')['sha256'] == REVIEW_HANDOFF, 'Independent V5 handoff changed')
    handoff = json.loads((ORIGINAL / 'handoff.json').read_bytes())
    require(sha(stable(handoff['members'])) == handoff['memberTreeSHA256'], 'Frozen member tree differs')
    names = ['prepare.py', 'adapter.py', 'importer.py', 'test_importer.py', 'packet.json',
             'runtime-source-manifest.json', 'runtime-sources.tar.gz', 'selection-template.json',
             'input-bindings.json', 'frozen-inputs.tar.gz']
    result = {}
    for name in names:
        path = ORIGINAL / name; relative = str(path.relative_to(ROOT))
        expected = handoff['members'][relative]
        require(row(path) == expected, 'Frozen V5 referenced member changed: ' + name)
        result[relative] = expected
    require(result[str((ORIGINAL / 'packet.json').relative_to(ROOT))]['sha256'] == ORIGINAL_PACKET,
            'Original V5 packet identity differs')
    for path in [ORIGINAL / 'handoff.json', REVIEW / 'handoff.json',
                 ROOT / 'verification/apple-focus-reference-runtime-v5-root-review/independent-decision.json']:
        result[str(path.relative_to(ROOT))] = row(path)
    decision = json.loads((ROOT / 'verification/apple-focus-reference-runtime-v5-root-review/independent-decision.json').read_bytes())
    require(decision['status'] == 'rejected-for-fresh-native-selection' and 'V5-001' in decision['finding'],
            'Root namespace-correction decision differs')
    return result


def original_payload():
    source = json.loads((ORIGINAL / 'runtime-source-manifest.json').read_bytes())
    return archive_payload(ORIGINAL / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')


def frozen_product_inputs():
    # Read exactly these two data members from the immutable, referenced V5
    # archive. Do not reconstruct or import its historical packet closure.
    binding = json.loads((ORIGINAL / 'input-bindings.json').read_bytes())
    require(row(ORIGINAL / 'frozen-inputs.tar.gz') == binding['archive'], 'Immutable V5 input archive changed')
    result = {}
    with tarfile.open(ORIGINAL / 'frozen-inputs.tar.gz', 'r:gz') as archive:
        members = archive.getmembers()
        require(len({member.name for member in members}) == len(members), 'Duplicate immutable input member')
        for filename in ['product-manifest.json', 'products.tar.gz']:
            logical = PRODUCT_PREFIX + filename
            stored = binding['storage'][logical]
            member = archive.getmember(stored)
            require(member.isfile(), 'Regular immutable product input required')
            raw = archive.extractfile(member).read()
            require({'kind': 'file', 'mode': member.mode, 'bytes': len(raw), 'sha256': sha(raw)}
                    == binding['bindings'][logical], 'Frozen native product input differs')
            result[filename] = raw
    require(sha(result['products.tar.gz']) == PRODUCT, 'Frozen native product archive differs')
    products = json.loads(result['product-manifest.json'])
    require(products['archive']['sha256'] == PRODUCT and set(row['kind'] for row in products['products'].values()) == {'file'},
            'Original regular product manifest required')
    return result


def prepare():
    require(not (BASE / 'packet.json').exists(), 'Preserve previous correction packet')
    bindings = references()
    original = original_payload(); corrected = dict(original)
    adapter = (ORIGINAL / 'adapter.py').read_bytes()
    require(adapter.count(OLD_PREFIX) == 1 and original['join_support.py'].count(OLD_PREFIX) == 1,
            'Exactly one affected prefix in each adapter copy required')
    corrected_adapter = adapter.replace(OLD_PREFIX, NEW_PREFIX, 1)
    corrected['join_support.py'] = original['join_support.py'].replace(OLD_PREFIX, NEW_PREFIX, 1)
    require(corrected['join_support.py'].endswith(corrected_adapter), 'Selected adapter suffix differs')
    require([name for name in original if original[name] != corrected[name]] == ['join_support.py'], 'Unexpected selected change')
    scratch = Path(tempfile.mkdtemp(prefix='prepare-owned-', dir=BASE))
    try:
        rows = manifest(corrected); materialize(scratch / 'selected', rows, corrected)
        archive = archive_sources(BASE / 'runtime-sources.tar.gz', scratch / 'selected', rows)
    finally:
        shutil.rmtree(scratch)
    dispatch_old = (ORIGINAL / 'prepare.py').read_text().split('\ndef dispatch(', 1)[1].split("\n\nif __name__", 1)[0]
    dispatch_new = dispatch_old.replace("'native-run-v4-'", "'native-run-v5-'")
    require(dispatch_old.count("'native-run-v4-'") == 1, 'One frozen dispatch prefix required')
    local_dispatch = Path(__file__).read_text().split('\ndef _dispatch(', 1)[1].split('\n\n@contextlib.contextmanager', 1)[0]
    require(local_dispatch == dispatch_new, 'Dispatch body differs beyond the single prefix correction')
    patch = ''.join(difflib.unified_diff(dispatch_old.splitlines(True), dispatch_new.splitlines(True),
                                       fromfile='frozen-v5/prepare.py:dispatch', tofile='correction/prepare.py:_dispatch'))
    for name, old, new in [('adapter.py', adapter, corrected_adapter), ('selected/join_support.py', original['join_support.py'], corrected['join_support.py'])]:
        patch += ''.join(difflib.unified_diff(old.decode().splitlines(True), new.decode().splitlines(True),
                                            fromfile='frozen-v5/' + name, tofile='correction/' + name))
    for name, raw in [('adapter.py', corrected_adapter), ('importer.py', original['importer.py']),
                      ('runtime-source-manifest.json', stable(archive)),
                      ('selection-template.json', (ORIGINAL / 'selection-template.json').read_bytes()),
                      ('correction.patch', patch.encode())]:
        with (BASE / name).open('xb') as stream:
            stream.write(raw)
    products = frozen_product_inputs()
    packet = {'schema': 'mixer.apple-focus-reference-runtime-packet.5', 'derivative': 'V5-001-output-prefix-only',
              'scope': 'Host preparation only; separate independent root review and fresh selection required',
              'outputPrefix': 'native-run-v5-', 'originalPacketSHA256': ORIGINAL_PACKET,
              'references': bindings, 'sourceRevisionLabel': 'ba9ad4372f94463ba4d363cdfd76dd565c96413f',
              'sourceRevisionMeaning': 'Inherited frozen compile label; exact hashes define this derivative; no Git query',
              'selectedSourceTreeSHA256': archive['treeSHA256'], 'unchangedSelectedFiles': len(original) - 1,
              'changedSelectedFiles': ['join_support.py'], 'nativeProductArchiveSHA256': PRODUCT,
              'nativeProductManifestSHA256': sha(products['product-manifest.json']),
              'files': {name: row(BASE / name) for name in SOURCES + ARTIFACTS},
              'nativeExecuted': False, 'runtimeSelected': False, 'compileRerun': False, 'gaAccepted': False,
              'physicalPhones': 'disconnected-deferred'}
    with (BASE / 'packet.json').open('xb') as stream:
        stream.write(stable(packet))
    receipt = {'schema': 1, 'command': [sys.executable, '-B', str(BASE / 'prepare.py'), 'prepare'],
               'observedUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'python': sys.version,
               'pythonExecutable': str(Path(sys.executable).resolve()), 'packetSHA256': sha(stable(packet)),
               'sourceTreeSHA256': sha(stable(packet['files'])), 'referencesVerified': len(bindings),
               'selectedFiles': len(original), 'changedSelectedFiles': ['join_support.py'],
               'output': 'PASS: separate V5 prefix correction packet prepared; no native dispatch',
               'cleanup': {'ownedPreparationScratchAbsent': not scratch.exists(), 'nativeInstancesCreatedOrQueried': 0,
                           'servicesStarted': 0, 'otherProjectsTouched': False},
               'nativeExecuted': False, 'gitOrDependencyChanges': False}
    with (BASE / 'preparation-receipt.json').open('xb') as stream:
        stream.write(stable(receipt))
    print(receipt['output'])


def verify():
    packet = json.loads((BASE / 'packet.json').read_bytes())
    require(references() == packet['references'], 'Correction input references changed')
    for name, expected in packet['files'].items():
        require(row(BASE / name) == expected, 'Correction packet member changed: ' + name)
    source = json.loads((BASE / 'runtime-source-manifest.json').read_bytes())
    corrected = archive_payload(BASE / 'runtime-sources.tar.gz', source['files'], source['archive']['sha256'], 'selected/')
    original = original_payload()
    require(set(corrected) == set(original), 'Selected inventory changed')
    require(sorted(name for name in original if original[name] != corrected[name]) == ['join_support.py'], 'Unexpected selected source change')
    require(corrected['join_support.py'] == original['join_support.py'].replace(OLD_PREFIX, NEW_PREFIX, 1), 'Selected prefix derivative differs')
    require((BASE / 'adapter.py').read_bytes() == (ORIGINAL / 'adapter.py').read_bytes().replace(OLD_PREFIX, NEW_PREFIX, 1), 'Adapter prefix derivative differs')
    require((BASE / 'importer.py').read_bytes() == original['importer.py'], 'V5 arithmetic/context/import behavior changed')
    require(sha(stable(source['files'])) == source['treeSHA256'] == packet['selectedSourceTreeSHA256'], 'Selected tree digest differs')
    return {'packetSHA256': sha((BASE / 'packet.json').read_bytes()), 'nativeExecuted': False,
            'scope': 'Original immutable references and exact derivative bytes/modes/archive only'}


def _dispatch(reviewed_packet, selection_path, selected_sha):
    # This branch is NOT called by preparation/tests/freeze. Root is responsible
    # for independent review, exact selected simulator ownership and command.
    verified=verify();require(reviewed_packet==verified['packetSHA256'],'Root reviewed packet hash differs')
    guard_spec=importlib.util.spec_from_file_location('_root_selection_guard',BASE/'importer.py')
    importer=importlib.util.module_from_spec(guard_spec);guard_spec.loader.exec_module(importer)
    selection_path=Path(selection_path)
    require(row(selection_path)['sha256']==selected_sha,'Root out-of-band selection hash differs')
    root=importer.validate_root(importer.parse(selection_path.read_bytes()),reviewed_packet,fresh=True)
    output=BASE/('native-run-v5-'+root['runID'])
    require(not output.exists() and not output.is_symlink(),'Fresh run output required; never replay a run')
    output.mkdir(mode=0o755)
    h=helpers(); product_manifest=json.loads((V1/'compile-attempt-1/product-manifest.json').read_bytes())
    source_manifest=json.loads((BASE/'runtime-source-manifest.json').read_bytes())
    payload=h.archive_payload(BASE/'runtime-sources.tar.gz',source_manifest['files'],source_manifest['archive']['sha256'],'selected/')
    h.materialize(output/'selected',source_manifest['files'],payload)
    product_payload=h.archive_payload(V1/'compile-attempt-1/products.tar.gz',product_manifest['products'],PRODUCT)
    h.materialize(output/'products',product_manifest['products'],product_payload)
    selection=json.loads((BASE/'selection-template.json').read_bytes())
    selection.update(repositoryRoot=str(ROOT),outputBase=str(output),productsRoot=str(output/'products'),productArchive=str(V1/'compile-attempt-1/products.tar.gz'),productManifest=product_manifest,trustedRootSelection=root,files={name:item['sha256'] for name,item in source_manifest['files'].items()})
    (output/'selected/runtime-selection.json').write_bytes(stable(selection))
    (output/'root-selection.json').write_bytes(selection_path.read_bytes())
    # Loading the packet-local composition is the explicit native dispatch boundary.
    sys.path.insert(0,str(output/'selected'))
    spec=importlib.util.spec_from_file_location('composition',output/'selected/composition.py')
    module=importlib.util.module_from_spec(spec);sys.modules['composition']=module
    try:
        spec.loader.exec_module(module)
        return module.h.run(sha((output/'selected/runtime-selection.json').read_bytes()))
    finally:
        # Product/source scratch is retired after exact post-run verification.
        # Preserve it on any mismatch for root recovery; never broad-delete.
        good=(h.tree(output/'products')==product_manifest['products'] and all((output/'selected'/name).read_bytes()==raw for name,raw in payload.items()))
        receipt={'verifiedBeforeRemoval':good,'paths':[str(output/'products'),str(output/'selected')],'scope':'Packet-owned source/product scratch only; result and observations retained'}
        if good:
            shutil.rmtree(output/'products');shutil.rmtree(output/'selected')
        receipt['scratchAbsent']=not (output/'products').exists() and not (output/'selected').exists()
        (output/'scratch-cleanup.json').write_bytes(stable(receipt))


@contextlib.contextmanager
def product_workspace():
    payload = frozen_product_inputs()
    scratch = Path(tempfile.mkdtemp(prefix='dispatch-products-owned-', dir=BASE))
    try:
        location = scratch / 'compile-attempt-1'; location.mkdir(mode=0o755)
        for name, raw in payload.items():
            with (location / name).open('xb') as stream:
                stream.write(raw)
        yield scratch
    finally:
        exact = all((scratch / 'compile-attempt-1' / name).is_file()
                    and not (scratch / 'compile-attempt-1' / name).is_symlink()
                    and (scratch / 'compile-attempt-1' / name).read_bytes() == raw for name, raw in payload.items())
        receipt = {'schema': 1, 'scope': 'Two immutable product data inputs staged for this dispatch only',
                   'verifiedBeforeRemoval': exact, 'path': str(scratch), 'sourceArchiveSHA256': PRODUCT}
        if exact:
            shutil.rmtree(scratch)
        receipt['scratchAbsent'] = not scratch.exists()
        # A unique, retained cleanup receipt; never overwrite a previous attempt.
        with (BASE / (scratch.name + '-cleanup.json')).open('xb') as stream:
            stream.write(stable(receipt))
        require(exact, 'Product input staging changed; preserve exact owned scratch for root recovery')


def dispatch(reviewed_packet, selection_path, selected_sha):
    global V1
    require(reviewed_packet == verify()['packetSHA256'], 'Root reviewed packet hash differs')
    require(V1 is None, 'Dispatch product workspace already selected')
    with product_workspace() as location:
        V1 = location
        try:
            return _dispatch(reviewed_packet, selection_path, selected_sha)
        finally:
            V1 = None


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'verify', 'dispatch'])
    parser.add_argument('--reviewed-packet')
    parser.add_argument('--root-selection')
    parser.add_argument('--root-selection-sha256')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'verify':
        print(json.dumps(verify(), sort_keys=True))
    else:
        dispatch(args.reviewed_packet, args.root_selection, args.root_selection_sha256)
