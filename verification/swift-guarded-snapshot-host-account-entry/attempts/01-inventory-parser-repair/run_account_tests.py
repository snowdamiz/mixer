#!/usr/bin/env python3
"""Finite standalone account tests; never links or calls Mixer product code."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc')

def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value): path.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')

def main():
    assert not (HERE/'seal.json').exists()
    scratch = HERE/'owned-account-work'
    scratch.mkdir(exist_ok=False)
    commands = HERE/'account-commands'
    commands.mkdir(exist_ok=False)
    roster = ['host_account.rs', 'account_test_driver.rs', 'negative_double_dispatch.rs',
              'negative_borrow_escape.rs', 'negative_cross_thread.rs']
    bindings = [dict(path=name, bytes=(HERE/name).stat().st_size,
                     sha256=sha((HERE/name).read_bytes())) for name in roster]
    env = dict(PATH='/usr/bin:/bin', TMPDIR=str(scratch))
    receipts = []
    def command(name, argv, expected, diagnostic=None):
        folder = commands/name
        folder.mkdir()
        start = time.monotonic()
        with (folder/'stdout').open('wb') as out, (folder/'stderr').open('wb') as err:
            child = subprocess.Popen(argv, cwd=HERE, env=env, stdout=out, stderr=err)
            try: code = child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=5); raise
        result = dict(name=name, argv=argv, cwd=str(HERE), environment=env,
                      elapsed_seconds=time.monotonic()-start, exit_code=code,
                      expected_exit_code=expected, direct_child_pid=child.pid,
                      direct_child_waited=True, input_bindings=bindings,
                      diagnostic=diagnostic,
                      output={n: dict(bytes=(folder/n).stat().st_size,
                                      sha256=sha((folder/n).read_bytes())) for n in ['stdout','stderr']},
                      scope='standalone fake-owner/callback host account only; no product crate/runtime')
        write(folder/'receipt.json', result)
        receipts.append(result)
        assert code == expected, (name, code)
        if diagnostic: assert diagnostic in (folder/'stderr').read_text()
        return folder
    try:
        version = command('compiler-version', [str(RUSTC),'--version','--verbose'], 0)
        for mode, optimize in [('debug','0'),('optimized','3')]:
            executable = scratch/f'account-{mode}'
            command(f'{mode}-compile', [str(RUSTC),'--edition=2021','--test',
                    '-C',f'opt-level={optimize}','-C','overflow-checks=yes','-C','panic=unwind',
                    str(HERE/'account_test_driver.rs'),'-o',str(executable)], 0)
            result = command(f'{mode}-run', [str(executable),'--test-threads=1'], 0)
            assert '11 passed; 0 failed' in (result/'stdout').read_text()
        for file, error in [('negative_double_dispatch.rs','E0382'),
                            ('negative_borrow_escape.rs','E0515'),
                            ('negative_cross_thread.rs','E0277')]:
            command(file.removesuffix('.rs'),[str(RUSTC),'--edition=2021',
                    '--emit=metadata='+str(scratch/(file+'.rmeta')),str(HERE/file)],1,error)
        write(HERE/'account-test-results.json', dict(schema=1,
              source_bindings=bindings, compiler_version=(version/'stdout').read_text(),
              compiler_sha256=sha(RUSTC.read_bytes()), commands=len(receipts),
              actual_tests_per_mode=11, modes=['debug','optimized'],
              negative_compile_controls=3, all_expected=True,
              pure_account_tests_not_genuine_ingress=True,
              production_grant_or_fixture_dispatched=False))
    finally:
        shutil.rmtree(scratch)
        write(HERE/'account-cleanup.json',dict(schema=1,owned_scratch_removed=not scratch.exists(),
              direct_children_waited=True, global_process_inventory=False,
              native_UI_capture_device_simulator_emulator_started=False,
              other_projects_inspected_or_changed=False))

if __name__ == '__main__': main()
