#!/usr/bin/env python3
"""Independent bounded, offline, owned-environment host-test supervisor."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

P = Path(__file__).absolute().parent
RUST = Path('/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin')
TOOLS = {'rustc':'dd6f58440b3418aa9157ae3f05d71eecff741ca41bc4eec120e7e8f2d933b9a0',
         'cargo':'fc7aa5077deca8abc0651f329e8ec1d968f520e996a93b428f9935014362b382'}
START = None
RECORDS = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def begin():
    global START
    assert START is None
    START = time.monotonic()
    for name, digest in TOOLS.items():
        assert sha(RUST/name) == digest
    for d in ['logs','scratch','artifacts','hostile','scratch/cargo-home']:
        (P/d).mkdir(parents=True,exist_ok=True)
    sentinel=P/'hostile/foreign-launcher'
    sentinel.write_text('#!/bin/sh\nprintf invoked > "'+str(P/'hostile/INVOKED')+'"\nexit 99\n')
    sentinel.chmod(0o700)
    (P/'hostile/keep').write_bytes(b'unchanged hostile inherited environment sentinel\n')


def environment(name, extra=None):
    inherited=os.environ.copy()
    sentinel=str(P/'hostile/foreign-launcher')
    injected={'RUST_TEST_THREADS':'999','RUST_TEST_SHUFFLE':'1','RUST_TEST_SKIP':'diagnostic_profile',
        'RUST_TEST_TIME_UNIT':'1,1','RUSTFLAGS':'--definitely-invalid-flag',
        'RUSTC_WRAPPER':sentinel,'RUSTC_WORKSPACE_WRAPPER':sentinel,'RUSTC':sentinel,
        'CARGO_BUILD_RUSTC':sentinel,'CARGO_BUILD_TARGET':'not-a-target',
        'CARGO_ENCODED_RUSTFLAGS':'--definitely-invalid-flag','RUSTUP_TOOLCHAIN':'missing-no-install',
        'TMPDIR':str(P/'hostile/TMPDIR'),'TMP':str(P/'hostile/TMP'),'TEMP':str(P/'hostile/TEMP')}
    inherited.update(injected)
    removed=sorted(k for k in inherited if k.startswith(('RUST','CARGO_')) or k in ('TMPDIR','TMP','TEMP'))
    actual={k:v for k,v in inherited.items() if k not in removed}
    tmp=P/'scratch/tmp'/name
    assert tmp.is_absolute() and '..' not in tmp.parts
    tmp.mkdir(parents=True,exist_ok=False)
    actual.update({'TMPDIR':str(tmp),'TMP':str(tmp),'TEMP':str(tmp),
        'CARGO_HOME':str(P/'scratch/cargo-home'),'CARGO_NET_OFFLINE':'true',
        'CARGO_TARGET_DIR':str(P/'scratch/cargo-target'), 'RUSTC':str(RUST/'rustc'),
        'RUSTUP_AUTO_INSTALL':'0','RUST_TEST_THREADS':'1'})
    if extra:
        for k,v in extra.items():
            assert k.startswith('MIXER_PROFILE_'), k
            actual[k]=str(v)
    return actual, {'injected':injected, 'removed_names':removed,
        'fixed':{k:actual[k] for k in ['TMPDIR','TMP','TEMP','CARGO_HOME','CARGO_TARGET_DIR','CARGO_NET_OFFLINE','RUSTC','RUSTUP_AUTO_INSTALL','RUST_TEST_THREADS']}}


def run(name, argv, extra=None, expect=0):
    assert START is not None and time.monotonic()-START < 600
    assert name not in [r['name'] for r in RECORDS]
    actual,controls=environment(name,extra)
    at=datetime.now(timezone.utc).isoformat(); tick=time.monotonic()
    child=subprocess.Popen([str(x) for x in argv],cwd=P,env=actual,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    timed_out=False
    try:
        out,err=child.communicate(timeout=min(60,600-(time.monotonic()-START)))
    except subprocess.TimeoutExpired:
        timed_out=True
        os.killpg(child.pid,signal.SIGKILL)
        out,err=child.communicate(timeout=min(60,max(0.01,660-(time.monotonic()-START))))
    finally:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    assert child.returncode is not None
    record={'name':name,'argv':[str(x) for x in argv],'cwd':str(P),'at':at,
        'elapsed_seconds':time.monotonic()-tick,'timeout_seconds':60,'timed_out':timed_out,
        'exit_code':child.returncode,'expected_exit_code':expect,'owned_child_reaped':True,
        'environment':controls}
    for label,data in [('stdout',out),('stderr',err)]:
        assert len(data)<16*1024*1024, 'unexpected unbounded test output'
        (P/'logs'/f'{name}.{label}').write_bytes(data)
        record[label]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (P/'logs'/f'{name}.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
    RECORDS.append(record)
    print(f'{name}: exit={child.returncode} timeout={timed_out} seconds={record["elapsed_seconds"]:.3f}',flush=True)
    assert not timed_out and child.returncode==expect, name
    assert not (P/'hostile/INVOKED').exists()
    assert (P/'hostile/keep').read_bytes()==b'unchanged hostile inherited environment sentinel\n'
    return out.decode(errors='replace'),err.decode(errors='replace')


def summary():
    (P/'commands.json').write_text(json.dumps({'schema':1,'active_limit_seconds':600,
        'cleanup_retention_limit_seconds':60,'per_child_limit_seconds':60,
        'elapsed_seconds':time.monotonic()-START,'commands':RECORDS,
        'hostile_sentinels_unchanged':not (P/'hostile/INVOKED').exists(),
        'no_Git_native_UI_capture_or_process_inventory':True},sort_keys=True,indent=2)+'\n')
