#!/usr/bin/env python3
"""Filesystem-only controls for exact phase membership; never launches a child."""
from pathlib import Path
import importlib.util
import json
import os
import tempfile
import time


def run(runner_path):
    started = time.monotonic()
    deadline = started + 55
    spec = importlib.util.spec_from_file_location('fixture_boundary_runner', runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    required = ['runtime.json', 'exunit-result.json', 'selection.json', 'postconditions.json'] + [
        'openssl-%02d.json' % n for n in range(1, 5)]
    expected = required + ['command.json', 'stdout.txt']
    results = []
    with tempfile.TemporaryDirectory(prefix='mixer-fixture-membership-controls-', dir='/private/tmp') as temporary:
        root = Path(temporary)

        def case(name, mutation=None):
            directory = root / name
            directory.mkdir()
            for filename in expected:
                (directory / filename).write_bytes(b'fixture bytes\n')
            if mutation is not None:
                mutation(directory)
            rejected = False
            try:
                runner.validate_phase_directory(directory, required, deadline)
            except ValueError:
                rejected = True
            if rejected != (mutation is not None):
                raise AssertionError('incorrect boundary decision for ' + name)
            results.append({'name': name, 'rejected': rejected})

        case('exact-ten-ordinary-files')
        case('extra-openssl-05', lambda path: (path / 'openssl-05.json').write_text('{}'))
        case('extra-file', lambda path: (path / 'extra.txt').write_text('unexpected'))
        case('missing-required', lambda path: (path / 'runtime.json').unlink())

        def symlink(path):
            target = path / 'runtime.json'
            target.unlink()
            target.symlink_to(path / 'selection.json')

        def directory(path):
            target = path / 'runtime.json'
            target.unlink()
            target.mkdir()

        def fifo(path):
            target = path / 'runtime.json'
            target.unlink()
            os.mkfifo(target)

        case('required-symlink', symlink)
        case('required-directory', directory)
        case('required-fifo', fifo)
        target = root / 'exact-ten-ordinary-files'
        link = root / 'phase-directory-symlink'
        link.symlink_to(target, target_is_directory=True)
        try:
            runner.validate_phase_directory(link, required, deadline)
        except ValueError:
            results.append({'name': 'phase-directory-symlink', 'rejected': True})
        else:
            raise AssertionError('symlink phase directory accepted')
        # The validator must not erase or repair rejected evidence.
        assert (root / 'extra-openssl-05/openssl-05.json').read_text() == '{}'
        assert (root / 'extra-file/extra.txt').read_text() == 'unexpected'
        assert (root / 'required-directory/runtime.json').is_dir()
        assert (root / 'required-symlink/runtime.json').is_symlink()
        evidence_preserved = True
    return {'schema': 1, 'status': 'passed',
            'scope': 'Offline Python filesystem boundary controls only; no child or product runtime',
            'ordinary_files_expected': 10, 'required_artifacts': 8, 'controls': results,
            'rejected_fixture_evidence_preserved_by_validator': evidence_preserved,
            'exact_temporary_control_tree_removed': not root.exists(),
            'compiler_or_runtime_invocations': 0,
            'elapsed_seconds': round(time.monotonic() - started, 6)}


if __name__ == '__main__':
    import sys
    print(json.dumps(run(Path(sys.argv[1])), indent=2))
