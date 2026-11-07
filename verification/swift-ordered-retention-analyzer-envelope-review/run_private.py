#!/usr/bin/env python3
"""Frozen regression and independent private controls on owned test-only append."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
FREEZE = BASE / 'implementation-review-1'
PRODUCER = ROOT / 'verification/swift-ordered-retention-analyzer-envelope'
RUSTC = Path('/Users/andreyyurlov/.rustup/toolchains/stable-aarch64-apple-darwin/bin/rustc')
SEAL = 'ea5214e8571277e0a289bb44add5716d8c30e5d0bf3332939f18575ecf3d4eae'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        while block := source.read(65536): h.update(block)
    return h.hexdigest()

def frozen():
    p = PRODUCER / 'seal.json'; assert sha(p) == SEAL
    value = json.loads(p.read_text()); assert len(value['members']) == 796
    for member in value['members']:
        source = ROOT / member['path']
        assert source.stat().st_size == member['bytes'] and sha(source) == member['sha256'], member['path']
    return value

def main():
    name = sys.argv[1]; assert name.startswith('run-') and name[4:].isdigit()
    mode = sys.argv[2] if len(sys.argv) > 2 else 'all'
    assert mode in ('all', 'private-only')
    run = FREEZE / 'private' / name; run.mkdir(parents=True)
    scratch = BASE / 'scratch' / ('private-' + name); scratch.mkdir(parents=True)
    for child in ['review', 'foundation', 'envelope']: (scratch / child).mkdir()
    shutil.copy2(__file__, run / 'executed-runner.py')
    receipt = dict(schema=1, at_unix=time.time(), scope='Frozen methods and independent actualRust private boundary methods', mode=mode, commands=[], passed=False,
                   producer_seal_sha256=SEAL, native_capture_or_device_execution=False)
    def write(): (run/'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    def command(label, args, env=None):
        started = time.time()
        child = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, stderr = child.communicate(timeout=60)
        except subprocess.TimeoutExpired as error:
            os.killpg(child.pid, signal.SIGKILL)
            stdout, stderr = child.communicate()
            (run/(label+'.stdout')).write_bytes(stdout); (run/(label+'.stderr')).write_bytes(stderr)
            receipt['commands'].append(dict(label=label,argv=[str(x) for x in args],cwd=str(ROOT),timed_out=True,timeout_seconds=60,
                owned_process_group=child.pid,group_killed=True,direct_child_reaped=True,returncode=child.returncode,
                stdout_sha256=sha(run/(label+'.stdout')),stderr_sha256=sha(run/(label+'.stderr'))))
            write(); raise
        result = subprocess.CompletedProcess(args,child.returncode,stdout,stderr)
        (run/(label+'.stdout')).write_bytes(stdout); (run/(label+'.stderr')).write_bytes(stderr)
        receipt['commands'].append(dict(label=label, argv=[str(x) for x in args], cwd=str(ROOT), returncode=child.returncode,owned_process_group=child.pid,direct_child_reaped=True,
            elapsed_seconds=time.time()-started, timeout_seconds=60, stdout_sha256=sha(run/(label+'.stdout')), stderr_sha256=sha(run/(label+'.stderr'))))
        write(); assert result.returncode == 0, label
        return result
    try:
        packet = frozen(); receipt['producer_before_members'] = len(packet['members'])
        receipt['revision_start'] = command('revision-start', ['git','rev-parse','HEAD']).stdout.decode().strip()
        command('python-version', [sys.executable,'--version']); command('rust-version',[str(RUSTC),'--version','--verbose'])
        receipt['tools'] = dict(python=dict(path=sys.executable,sha256=sha(Path(sys.executable)),version=sys.version),rustc=dict(path=str(RUSTC),sha256=sha(RUSTC)))
        prefix = 'verification/swift-ordered-retention-analyzer-envelope/commands/run-6/'
        copied = []
        for member in packet['members']:
            if not member['path'].startswith(prefix): continue
            relative = member['path'][len(prefix):]
            if not (relative.startswith('harness/') or relative.startswith('sources/inputs/historical/')): continue
            target = run/'frozen-regression'/relative; target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(ROOT/member['path'],target)
            copied.append(member)
        receipt['frozen_regression_members'] = copied
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', MIXER_REVIEW_SCRATCH=str(scratch/'review'),
            MIXER_ANALYZER_LIBRARY_TEST_SCRATCH=str(scratch/'foundation'), MIXER_ENVELOPE_SCRATCH=str(scratch/'envelope'),
            MIXER_ANALYZER_LIBRARY_HISTORICAL=str(run/'frozen-regression/sources/inputs/historical'),
            MIXER_ENVELOPE_REVIEW_VECTORS=str(BASE/'corrected-vectors/profile-correction-1'))
        receipt['test_environment'] = {key:value for key,value in env.items() if key.startswith('MIXER_') or key=='PYTHONDONTWRITEBYTECODE'}
        if mode == 'all':
            regression = run/'regression-tests'
            command('compile-regression',[str(RUSTC),'--edition=2021','--test','-Dwarnings',str(run/'frozen-regression/harness/independent_tests.rs'),'-o',str(regression)])
            listing = command('regression-list',[str(regression),'--list'],env).stdout.decode()
            methods = [line[:-6] for line in listing.splitlines() if line.endswith(': test')]
            assert len(methods)==64
            for index,method in enumerate(methods):
                result=command(f'regression-{index:02}',[str(regression),'--test-threads=1','--nocapture','--exact',method],env)
                assert b'1 passed; 0 failed' in result.stdout
                print(f'Frozen regression method {index+1}/64 passed: {method}',flush=True)
            receipt['frozen_methods_passed']=64
        sources = run/'private-sources'; shutil.copytree(FREEZE/'sources',sources)
        oracle_path = 'verification/swift-ordered-retention-analyzer-envelope/inputs/oracle.bin'
        member = next(member for member in packet['members'] if member['path']==oracle_path)
        (sources/'inputs').mkdir(exist_ok=True); shutil.copy2(ROOT/oracle_path,sources/'inputs/oracle.bin')
        receipt['oracle']=member
        production = sources/'src/envelope.rs'; original = production.read_bytes()
        assert sha(production)=='80eb9830ed78b1122ff3ec0723e1ce20afb46fd4a4e5abf80c60c4883a65a84e'
        appendix = b'\n#[cfg(test)]\n#[path = "../private_boundary_tests.rs"]\nmod independent_boundary_review;\n'
        production.write_bytes(original+appendix)
        shutil.copy2(BASE/'private_boundary_tests.rs',sources/'private_boundary_tests.rs')
        assert production.read_bytes()[:len(original)]==original
        receipt['test_only_append']=dict(original_envelope_sha256=hashlib.sha256(original).hexdigest(),appendix=appendix.decode(),executed_envelope_sha256=sha(production),independent_controls_sha256=sha(sources/'private_boundary_tests.rs'))
        binary=run/'private-tests'
        command('compile-private',[str(RUSTC),'--edition=2021','--test','-Dwarnings',str(sources/'src/analyzer.rs'),'-o',str(binary)])
        result=command('private-tests',[str(binary),'--test-threads=1','--nocapture','review_'],env)
        assert b'10 passed; 0 failed' in result.stdout; receipt['private_methods_passed']=10
        receipt['passed']=True
    except BaseException:
        (run/'exception.stderr').write_text(traceback.format_exc()); raise
    finally:
        receipt['producer_after_members']=len(frozen()['members'])
        receipt['revision_end']=command('revision-end',['git','rev-parse','HEAD']).stdout.decode().strip()
        if any(scratch.iterdir()): shutil.move(str(scratch),str(run/'retained-scratch'))
        else: scratch.rmdir()
        if not any(scratch.parent.iterdir()): scratch.parent.rmdir()
        receipt['cleanup']='Exact owned scratch archived and removed after synchronous children returned; no process discovery'
        write()
    print(json.dumps(dict(passed=receipt['passed'],frozen_methods=receipt.get('frozen_methods_passed',0),private_methods=receipt.get('private_methods_passed',0),receipt=str((run/'receipt.json').relative_to(ROOT)))))

if __name__=='__main__':main()
