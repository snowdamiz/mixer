#!/usr/bin/env python3
"""Controlled host file fixtures for checker cleanup; no native runtime or target discovery."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
sys.path.insert(0, str(LANE))
from verify import remove_owned_extraction


def main():
    results = []
    for case in ['success', 'operation-failure', 'open-holder', 'symlink']:
        out = HERE / case
        out.mkdir()
        work = out / '.build'
        work.mkdir()
        fixture = work / 'fixture.bin'
        fixture.write_bytes(b'controlled checker cleanup fixture')
        expected = {'fixture.bin': {}}
        if case == 'operation-failure':
            failed = False
            try:
                try:
                    raise RuntimeError('controlled post-extraction operation failure')
                finally:
                    cleanup = remove_owned_extraction(work, out, expected)
            except RuntimeError as failure:
                failed = str(failure) == 'controlled post-extraction operation failure'
            assert failed and cleanup['status'] == 'removed' and not work.exists()
        elif case == 'open-holder':
            with fixture.open('rb'):
                refused = False
                try:
                    remove_owned_extraction(work, out, expected)
                except RuntimeError as failure:
                    refused = 'open holder' in str(failure)
                assert refused and fixture.exists()
                (out / 'extraction-open-holders.log').rename(out / 'refused-open-holder.log')
            cleanup = remove_owned_extraction(work, out, expected)
            assert cleanup['status'] == 'removed' and not work.exists()
        elif case == 'symlink':
            link = work / 'substituted-link'
            link.symlink_to(HERE / 'check.py')
            refused = False
            try:
                remove_owned_extraction(work, out, expected)
            except RuntimeError as failure:
                refused = 'symlink' in str(failure)
            assert refused and link.is_symlink() and (HERE / 'check.py').is_file()
            link.unlink()
            cleanup = remove_owned_extraction(work, out, expected)
        else:
            cleanup = remove_owned_extraction(work, out, expected)
            assert cleanup['status'] == 'removed' and not work.exists()
        results.append({'case': case, 'status': 'passed', 'cleanup': cleanup})
    receipt = {'status': 'passed', 'tests': results, 'scope': 'controlled host cleanup fixtures only; zero native execution',
               'checkerSHA256': hashlib.sha256((LANE / 'verify.py').read_bytes()).hexdigest(),
               'testSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (HERE / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'passed', 'controlledHostCleanupCases': len(results), 'allOwnedExtractionsRemoved': True}))


if __name__ == '__main__':
    main()
