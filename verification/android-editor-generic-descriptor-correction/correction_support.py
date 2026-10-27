"""Exact sealed data/source access for the correction; no archive/caches/scan."""
import hashlib
import importlib.abc
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / 'verification/android-editor-generic-descriptor-joins'
PREACCESS = ROOT / 'verification/android-generic-descriptor-join-independent'
REVIEW = PREACCESS / 'actual-review'
USED = {}
PACKETS = {
    'candidate': (CANDIDATE, 'seal.json', 'e8c7263060a98f05142ac1f31eb5b30d05a921fd8feeeb9d23de798cab4b3ad5'),
    'preaccess': (PREACCESS, 'preaccess-seal.json', 'e04efcdbeedfea4c8effc99d51bbe4ca63b2b4b1be21f22c7076ee0c89e5f236'),
    'review': (REVIEW, 'review-seal.json', '1dca5622d6f8602821e44013f4b5f09ba760f18d8660d0d0961c767c9a5cfd85'),
}


def ident(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def table(packet):
    root, name, expected = PACKETS[packet]
    raw = (root / name).read_bytes()
    assert ident(raw)['sha256'] == expected
    USED[str((root / name).relative_to(ROOT))] = ident(raw)
    return {item['path']: item for item in json.loads(raw)['members']}


def verified(packet, member):
    root, _, _ = PACKETS[packet]
    relative = PurePosixPath(member)
    assert not relative.is_absolute() and '..' not in relative.parts
    members = table(packet)
    assert member in members
    path = root
    for part in relative.parts:
        path /= part
        assert not path.is_symlink()
    raw = path.read_bytes()
    assert ident(raw) == {key: members[member][key] for key in ('bytes', 'sha256')}
    USED[str(path.relative_to(ROOT))] = ident(raw)
    return raw


def verify_preserved_packets():
    for name in PACKETS:
        for member in table(name):
            verified(name, member)
    return {name: {'members': len(table(name)), 'seal_sha256': PACKETS[name][2]} for name in PACKETS}


def source_module(name, raw, filename):
    result = types.ModuleType(name)
    result.__file__ = str(filename)
    sys.modules[name] = result
    exec(compile(raw, str(filename), 'exec'), result.__dict__)
    return result


def load_corrected():
    return source_module('check_descriptor_joins', (HERE / 'check_descriptor_joins.py').read_bytes(), HERE / 'check_descriptor_joins.py')


def baseline_joiner():
    """Only released original checker source + exact source-only data parser."""
    original = source_module('_original_descriptor_checker', verified('candidate', 'check_descriptor_joins.py'), CANDIDATE / 'check_descriptor_joins.py')
    data = (ROOT / original.PARSER).read_bytes()
    assert ident(data)['sha256'] == '211ad86c8b0ffd9048d322efbb9e93bc3fc6606dcf745788bb36ec6052adfd2d'
    USED[str(original.PARSER)] = ident(data)
    previous = importlib.util.spec_from_file_location

    class SourceOnlyLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            exec(compile(data, str(ROOT / original.PARSER), 'exec'), module.__dict__)

    def selected_spec(name, location, *args, **kwargs):
        assert name == '_sealed_data_classfile_reader' and Path(location) == ROOT / original.PARSER
        return importlib.util.spec_from_loader(name, SourceOnlyLoader(), origin=str(location))

    try:
        importlib.util.spec_from_file_location = selected_spec
        joiner = original.Joiner(original.Inputs())
    finally:
        importlib.util.spec_from_file_location = previous
    return original, joiner


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n')
