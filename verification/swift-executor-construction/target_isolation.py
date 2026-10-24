"""Keep product and metadata build artifacts separate and witness test binaries."""
from pathlib import Path
import hashlib
import re
import subprocess

DERIVED_TEST = 'experimental_swift_reactor::execution::frozen_construction_metadata'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SnapshotBuildIsolation:
    def __init__(self, out, source, metadata):
        self.out = Path(out).resolve()
        self.snapshots = {'source': Path(source).resolve(),
                          'derived_metadata': Path(metadata).resolve()}
        self.targets = {'source': self.out / 'build/product-target',
                        'derived_metadata': self.out / 'build/metadata-target'}
        assert self.snapshots['source'] != self.snapshots['derived_metadata']
        product = self.targets['source'].resolve()
        metadata_target = self.targets['derived_metadata'].resolve()
        assert product != metadata_target
        assert not product.is_relative_to(metadata_target)
        assert not metadata_target.is_relative_to(product)
        for target in self.targets.values():
            if target.exists():
                raise RuntimeError(f'Build target must be fresh: {target}')

    def kind(self, cwd):
        cwd = Path(cwd).resolve()
        matches = [kind for kind, root in self.snapshots.items() if cwd == root]
        assert len(matches) == 1, cwd
        return matches[0]

    def environment(self, base, cwd):
        target = self.targets[self.kind(cwd)].resolve()
        env = dict(base)
        env['CARGO_TARGET_DIR'] = str(target)
        env['CARGO_TERM_COLOR'] = 'never'
        return env

    def arguments(self, argv, cwd):
        argv = list(argv)
        if argv[0] == 'cargo' and len(argv) > 1 and argv[1] in ('test', 'run', 'check', 'clippy'):
            assert '--manifest-path' not in argv and '--target-dir' not in argv
            target = self.targets[self.kind(cwd)].resolve()
            argv[2:2] = ['--manifest-path', str(Path(cwd).resolve() / 'Cargo.toml'),
                         '--target-dir', str(target)]
        return argv

    def test_binary_witnesses(self, name, argv, output, cwd, env):
        if argv[:2] != ['cargo', 'test']:
            return []
        kind = self.kind(cwd)
        target = self.targets[kind].resolve()
        assert env['CARGO_TARGET_DIR'] == str(target)
        binaries = re.findall(r'^\s*Running unittests src/lib\.rs \(([^\n)]+)\)$',
                              output, flags=re.MULTILINE)
        assert len(binaries) == 1, (name, binaries)
        binary = Path(binaries[0]).resolve(strict=True)
        assert binary.is_relative_to(target), (binary, target)
        digest = sha(binary)
        command = [str(binary), '--list']
        result = subprocess.run(command, cwd=cwd, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = self.out / 'logs' / (name + '-binary-test-list.log')
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout)
        assert result.returncode == 0, (name, result.returncode)
        assert sha(binary) == digest, f'Executable changed while listing: {binary}'
        tests = [line.removesuffix(': test') for line in result.stdout.splitlines()
                 if line.endswith(': test')]
        derived = DERIVED_TEST in tests
        assert derived == (kind == 'derived_metadata'), (name, kind, derived)
        return [{'executable': str(binary), 'sha256': digest,
                 'target_dir': str(target), 'snapshot_kind': kind,
                 'runtime_test_count': len(tests), 'derived_probe_present': derived,
                 'list_argv': command, 'list_cwd': str(Path(cwd).resolve()),
                 'list_exit_code': result.returncode, 'list_log': str(log),
                 'list_log_sha256': sha(log)}]
