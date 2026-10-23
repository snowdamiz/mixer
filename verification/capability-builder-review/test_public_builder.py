"""Independent negative public-CLI probes; fixture repositories are not VM builds.

The candidate builder is copied byte-for-byte into a tiny private Git repository.
Only reviewed headers/contracts are reused; the fake Rust source is never compiled.
Each probe runs both normal Python and -O through the actual command-line entry.
"""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / 'experimental-capability-runtime/build-vm.py'
CANDIDATE = BUILDER.read_bytes()
RUSTC = Path(shutil.which('rustc') or '/opt/homebrew/opt/rustup/bin/rustc')
PIN = 'b25e3b7de2391a80d12e7fd75e60903495bec120'
INPUTS = ['vm/Cargo.toml', 'vm/Cargo.lock', 'vm/include/mixer_vm.h',
          'vm/include/mixer_vm_capability.h', 'contracts/vm-profile-v1.json',
          'contracts/vm-session-v1.json', 'contracts/guest-capability-transport-v1.json',
          'capabilities/schema/v1.json', 'capabilities/schema/hashes.json',
          'runtime/Sources/CMixerVM/include/mixer_vm.h']


def run(argv, cwd, **kwargs):
    return subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          timeout=30, **kwargs)


class PublicBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print('candidate_sha256=' + hashlib.sha256(CANDIDATE).hexdigest(), flush=True)
        print('harness_sha256=' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), flush=True)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='mixer-builder-public-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        for name in INPUTS:
            raw = subprocess.check_output(['git', 'show', f'{PIN}:{name}'], cwd=ROOT)
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        source = self.repo / 'vm/src/lib.rs'
        source.parent.mkdir(parents=True)
        source.write_text('// Independent negative fixture. Must never be compiled.\n')
        self.script = self.repo / 'experimental-capability-runtime/build-vm.py'
        self.script.parent.mkdir()
        self.script.write_bytes(CANDIDATE)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Mixer independent local test')
        self.git('config', 'user.email', 'local-test@example.invalid')
        self.commit()
        self.outside = self.base / 'outside'
        self.outside.mkdir()
        self.sentinel = self.outside / 'sentinel'
        self.sentinel.write_bytes(b'protected original bytes\n')
        self.before = self.snapshot(self.outside)

    def git(self, *args):
        result = run(['git', *args], self.repo)
        self.assertEqual(result.returncode, 0, result.stdout.decode(errors='replace'))
        return result.stdout.decode().strip()

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-qm', 'Independent fixture')
        self.revision = self.git('rev-parse', 'HEAD')

    def snapshot(self, directory):
        return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob('*') if p.is_file()}

    def reject(self, *, expected, revision=None, setup=None, before_output=False, rustc=None):
        for optimized in (False, True):
            with self.subTest(optimized=optimized):
                output = self.base / ('out-optimized' if optimized else 'out-normal')
                cache = self.base / ('cache-optimized' if optimized else 'cache-normal')
                if setup:
                    output, cache = setup(output, cache)
                argv = [sys.executable] + (['-O'] if optimized else []) + [str(self.script),
                    '--revision', revision or self.revision, '--target', 'host', '--output', str(output),
                    '--cache', str(cache), '--rustc', str(rustc or RUSTC)]
                result = run(argv, self.repo)
                diagnostic = result.stdout.decode(errors='replace')
                self.assertNotEqual(result.returncode, 0, diagnostic)
                self.assertRegex(diagnostic, expected)
                self.assertNotIn('Traceback', diagnostic)
                self.assertFalse((output / 'receipt.json').exists(), diagnostic)
                self.assertFalse((output / 'cargo-build.log').exists(), 'fixture reached a Cargo build')
                if before_output:
                    self.assertFalse(output.exists(), diagnostic)
                    self.assertFalse(cache.exists(), diagnostic)
                self.assertEqual(self.snapshot(self.outside), self.before)

    def test_revision_requires_full_commit(self):
        self.reject(expected='complete lowercase40hex commit', revision='HEAD', before_output=True)

    def test_changed_header_rejects_before_output(self):
        path = self.repo / 'vm/include/mixer_vm_capability.h'
        path.write_bytes(path.read_bytes() + b'\n/* unreviewed header */\n')
        self.commit()
        self.reject(expected='reviewed header mismatch', before_output=True)

    def test_missing_native_feature_rejects_before_output(self):
        path = self.repo / 'vm/Cargo.toml'
        path.write_text(path.read_text().replace('experimental-capability-native =', 'missing-native ='))
        self.commit()
        self.reject(expected='native feature chain/defaults mismatch', before_output=True)

    def test_implicit_build_script_rejects_before_output(self):
        (self.repo / 'vm/build.rs').write_text('fn main() { panic!("must not execute") }\n')
        self.commit()
        self.reject(expected='build scripts are outside', before_output=True)

    def test_git_tracked_source_symlink_rejects_before_output(self):
        (self.repo / 'vm/src/linked.rs').symlink_to(self.sentinel)
        self.commit()
        self.reject(expected='not a regular file', before_output=True)

    def test_git_submodule_entry_rejects_before_output(self):
        self.git('update-index', '--add', '--cacheinfo', f'160000,{self.revision},vm/src/foreign')
        self.git('commit', '-qm', 'Untrusted gitlink')
        self.revision = self.git('rev-parse', 'HEAD')
        self.reject(expected='not a regular file', before_output=True)

    def test_existing_output_is_not_overwritten(self):
        def setup(output, cache):
            output.mkdir()
            (output / 'keep').write_bytes(b'keep\n')
            self.addCleanup(lambda: self.assertEqual((output / 'keep').read_bytes(), b'keep\n'))
            return output, cache
        self.reject(expected='File exists', setup=setup)

    def test_output_symlink_is_not_followed(self):
        def setup(output, cache):
            output.symlink_to(self.outside, target_is_directory=True)
            return output, cache
        self.reject(expected='File exists', setup=setup)

    def test_output_ancestor_symlink_is_not_followed(self):
        def setup(output, cache):
            output.symlink_to(self.outside, target_is_directory=True)
            return output / 'escaped-child', cache
        self.reject(expected='Not a directory|Too many levels', setup=setup)

    def test_cache_inside_output_is_rejected_before_creation(self):
        self.reject(expected='paths overlap', setup=lambda output, cache: (output, output / 'nested-cache'), before_output=True)

    def test_cache_external_hardlink_preserves_outside_file(self):
        def setup(output, cache):
            cache.mkdir(mode=0o700)
            os.link(self.sentinel, cache / 'linked-object')
            return output, cache
        self.reject(expected='cache has an external hardlink', setup=setup)

    def test_cache_symlink_preserves_outside_tree(self):
        def setup(output, cache):
            cache.mkdir(mode=0o700)
            (cache / 'linked-directory').symlink_to(self.outside, target_is_directory=True)
            return output, cache
        self.reject(expected='cache has a symlink or special file', setup=setup)

    def test_output_limit_stops_descendant_writes(self):
        # Controlled fake compiler selector only; this is process cleanup evidence,
        # not execution of an actual Rust compiler or a successful VM build.
        selector = self.base / 'flooding-selector'
        ticks = self.base / 'descendant-ticks'
        child = ('import time\nfrom pathlib import Path\np=Path(' + repr(str(ticks)) + ')\n'
                 'end=time.monotonic()+10\nwhile time.monotonic()<end:\n'
                 ' with p.open("ab") as f: f.write(b"x")\n time.sleep(0.01)\n')
        selector.write_text('#!' + sys.executable + '\nimport subprocess,sys,time\n'
            'subprocess.Popen([sys.executable,"-c",' + repr(child) + '],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
            'time.sleep(0.15)\nsys.stdout.buffer.write(b"x"*(3*1024*1024))\nsys.stdout.buffer.flush()\ntime.sleep(15)\n')
        selector.chmod(0o700)
        try:
            self.reject(expected='rust-sysroot failed', rustc=selector)
            self.assertTrue(ticks.exists(), 'descendant was not started')
            before = ticks.read_bytes()
            time.sleep(0.15)
            self.assertEqual(ticks.read_bytes(), before, 'descendant still mutating files after rejection')
        finally:
            # Even a defective candidate's test child is intrinsically limited to10s.
            # Delay private temporary-directory removal if a regression kept it alive.
            if ticks.exists():
                before = ticks.stat().st_size
                time.sleep(0.03)
                if ticks.stat().st_size != before:
                    time.sleep(10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
