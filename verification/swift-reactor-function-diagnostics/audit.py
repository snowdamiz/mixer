"""Verify the final diagnostic receipts and their retained artifacts read-only."""
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def main():
    results = []
    for directory in [HERE / '2026-10-23-reactor-final-v2', ROOT / 'compiler/experiments/profile-budget/functions/evidence/2026-10-23-command-compatibility-v2']:
        path = directory / 'receipt.json'
        record = json.loads(path.read_text())
        assert record['authorization'] is False and record['valid'] is False
        assert record['production_limits_changed'] is False
        assert record['status'] == 'measurement complete; per-body rejections recorded; no module authorization or execution'
        for relative, expected in record['source_manifest'].items():
            assert digest(ROOT / relative) == expected, relative
        for key in ['artifact', 'link_map', 'binary']:
            assert digest(record[key]['path']) == record[key]['sha256'], key
        for command in record['commands']:
            assert command['exitCode'] == 0 and not command['timedOut'] and not command['outputLimitExceeded']
            assert digest(command['executable']['path']) == command['executable']['sha256']
            for key in ['stdout', 'stderr']:
                item = command[key]
                value = directory / item['path']
                assert value.stat().st_size == item['bytes'] and digest(value) == item['sha256']
        for key in ['statistics', 'function_attribution']:
            assert digest(directory / record[key]['path']) == record[key]['sha256']
        compressed = directory / record['all_functions']['path']
        assert digest(compressed) == record['all_functions']['gzipSHA256']
        with gzip.open(compressed, 'rb') as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        assert len(raw) <= 16 * 1024 * 1024
        assert len(raw) == record['all_functions']['rawBytes']
        assert hashlib.sha256(raw).hexdigest() == record['all_functions']['rawSHA256']
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        stats = json.loads((directory / record['statistics']['path']).read_text())
        attribution = json.loads((directory / record['function_attribution']['path']).read_text())
        assert len(rows) == stats['function_count'] == record['observed']['functions'] == attribution['verified_function_count']
        assert all(int(row['defined']) == index and int(row['function']) == index + record['observed']['imports'] for index, row in enumerate(rows))
        assert max(int(row['raw_max_operand_height']) for row in rows) == stats['static_maximum_operand_height']
        retained_work = Path(record['binary']['path']).parents[1]
        assert digest(retained_work / 'source.tar') == record['source_archive_sha256']
        assert digest(retained_work / 'functions.csv') == record['all_functions']['rawSHA256']
        assert digest(retained_work / 'candidate.wasm') == record['artifact']['sha256']
        results.append({'receipt': str(path.relative_to(ROOT)), 'sha256': digest(path), 'sourceDigest': record['source_digest'], 'functions': len(rows), 'commandsVerified': len(record['commands']), 'retainedExecutableVerified': True, 'authorization': False, 'valid': False})
    result = {'status': 'passed-read-only-binding-audit', 'authorization': False, 'valid': False, 'command': [sys.executable, '-B', str(Path(__file__).resolve())], 'pythonVersion': sys.version, 'pythonSHA256': digest(sys.executable), 'auditSourceSHA256': digest(__file__), 'results': results, 'scope': 'Current source/log/tool/archive/artifact/complete-CSV bindings only; not independent VM correctness, profile admission or execution.'}
    (HERE / 'audit.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
