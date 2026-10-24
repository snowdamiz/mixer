"""Read-only, standard-library evidence helpers; no native tool entry points."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/android-toggle-keyboard-fixture-diagnosis'
RUNTIME = PRODUCER / 'runtime/runtime-1'
RESET = ROOT / 'verification/android-toggle-scroll-reset-fix'
PRODUCER_SEAL = '4c3c59761c0b13a0376b7d0c2ecd1de11b2dc2b87a58c746026899452492bd36'
RUNTIME_SEAL = 'd94c3610872f155124827cda0eb74d08554f9984a7b7fafdc9f98ebb8350f7af'


def need(value, message):
    if not value:
        raise ValueError(message)


def data_bind(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def bind(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink(), 'regular evidence file required ' + str(path))
    return data_bind(path.read_bytes())


def read_bytes(data):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key ' + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('nonfinite JSON constant ' + value)

    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def read(path):
    return read_bytes(Path(path).read_bytes())


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def directory_bind(folder, excluded=()):
    values = {}
    for path in sorted(folder.rglob('*')):
        need(not path.is_symlink(), 'evidence symlink ' + str(path))
        if path.is_file() and path not in excluded:
            values[str(path.relative_to(folder))] = bind(path)
    return values


def check_upstream():
    need(bind(PRODUCER / 'packet-seal.json')['sha256'] == PRODUCER_SEAL, 'root-selected producer seal drift')
    packet = read(PRODUCER / 'packet-seal.json')
    need(set(packet) == {'schema', 'files'} and packet['schema'] == 1, 'producer seal schema')
    actual = {}
    for path in sorted(PRODUCER.rglob('*')):
        need(not path.is_symlink(), 'producer symlink')
        if path.is_relative_to(PRODUCER / 'runtime') or path == PRODUCER / 'packet-seal.json':
            continue
        if path.is_file():
            actual[str(path.relative_to(ROOT))] = bind(path)
    doc = ROOT / 'docs/android-toggle-keyboard-fixture-diagnosis.md'
    actual[str(doc.relative_to(ROOT))] = bind(doc)
    need(actual == packet['files'], 'producer sealed file set or bytes drift')
    seal = RUNTIME / 'artifact-seal.json'
    need(bind(seal)['sha256'] == RUNTIME_SEAL, 'root-run runtime seal drift')
    need(directory_bind(RUNTIME, (seal,)) == read(seal), 'runtime sealed file set or bytes drift')
    return {'producerPacketSeal': bind(PRODUCER / 'packet-seal.json'),
            'producerSealedFiles': len(actual), 'runtimeSeal': bind(seal),
            'runtimeSealedFiles': len(read(seal)),
            'nativeRawExport': bind(RUNTIME / 'toggle-supplement-results.json'),
            'originalFailedResetExport': bind(RESET / 'runtime/runtime-1/toggle-supplement-results.json'),
            'originalFailedResetReceipt': bind(RESET / 'runtime/runtime-1/receipt.json')}
