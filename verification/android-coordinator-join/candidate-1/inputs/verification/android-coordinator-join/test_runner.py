#!/usr/bin/env python3
"""Headless safety guards only. These tests neither discover nor launch native targets."""
import importlib.util
from pathlib import Path
import tarfile
import unittest

spec = importlib.util.spec_from_file_location('join_runner', Path(__file__).with_name('run.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class RunnerGuards(unittest.TestCase):
    def test_only_exact_owned_pid_port_avd_can_authorize_stop(self):
        valid = '123 /sdk/emulator/qemu/darwin-aarch64/qemu-system-aarch64 -avd megpt-parity-api37 -port 5586 -read-only'
        self.assertTrue(runner.owned_identity(valid, 123))
        for invalid in [valid.replace('123 ', '124 ', 1), valid.replace('5586', '55860'),
                        valid.replace('api37', 'api37-other'), valid.replace('qemu-system-aarch64', 'other-process'),
                        valid + ' -port 5586', valid.replace('-port 5586', '--port 5586')]:
            self.assertFalse(runner.owned_identity(invalid, 123), invalid)

    def test_archive_refuses_traversal_links_duplicates_and_unsealed_members(self):
        good = tarfile.TarInfo('coordinator-join.apk')
        runner.validate_members([good], {'coordinator-join.apk': {}})
        for member in [tarfile.TarInfo('../outside'), tarfile.TarInfo('/absolute')]:
            with self.assertRaises(ValueError):
                runner.validate_members([member], {member.name: {}})
        link = tarfile.TarInfo('coordinator-join.apk')
        link.type = tarfile.SYMTYPE
        with self.assertRaises(ValueError):
            runner.validate_members([link], {'coordinator-join.apk': {}})
        with self.assertRaises(ValueError):
            runner.validate_members([good, good], {'coordinator-join.apk': {}})
        with self.assertRaises(ValueError):
            runner.validate_members([good], {'other.apk': {}})

    def test_runtime_contract_is_exact_and_rejects_physical_or_unqualified_api(self):
        target = {'ro.kernel.qemu': '1', 'ro.product.model': 'sdk_gphone64_arm64',
                  'ro.build.version.sdk': '37', 'ro.product.cpu.abi': 'arm64-v8a',
                  'ro.build.fingerprint': runner.FINGERPRINT, 'ro.boot.qemu.avd_name': runner.AVD,
                  'sys.boot_completed': '1'}
        runner.validate_target(target)
        for key, value in [('ro.kernel.qemu', '0'), ('ro.build.version.sdk', '36'),
                           ('ro.product.cpu.abi', 'x86_64'), ('ro.boot.qemu.avd_name', 'unrelated'),
                           ('ro.build.fingerprint', 'different-image')]:
            with self.assertRaises(ValueError):
                runner.validate_target(dict(target, **{key: value}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
