#!/usr/bin/env python3
"""Build a frozen owned VM static library for the Swift native wrapper.

Only libmixer_vm.a is staged in lib/. Never point Swift's -L at Cargo's directory,
which also contains a dynamic library and can silently select it on macOS.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision', default='HEAD')
    parser.add_argument('--target', choices=['host','ios','ios-simulator','android'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ndk', type=Path)
    args = parser.parse_args()
    if args.target == 'android' and not args.ndk:
        parser.error('--ndk is required for Android')
    revision = subprocess.check_output(['git','rev-parse',args.revision+'^{commit}'],cwd=ROOT,text=True).strip()
    output = args.output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    archive = subprocess.check_output(['git','archive',revision,'vm','contracts/vm-session-v1.json'],cwd=ROOT)
    source = output/'source'
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(source,filter='data')
    header = source/'vm/include/mixer_vm.h'
    if header.read_bytes() != (ROOT/'runtime/Sources/CMixerVM/include/mixer_vm.h').read_bytes():
        raise ValueError('Swift wrapper header differs from frozen VM')
    env = dict(os.environ,PATH='/opt/homebrew/opt/rustup/bin:'+os.environ['PATH'],CARGO_TARGET_DIR=str(output/'target'))
    target = {'host':None,'ios':'aarch64-apple-ios','ios-simulator':'aarch64-apple-ios-sim','android':'aarch64-linux-android'}[args.target]
    if args.target.startswith('ios'):
        env['IPHONEOS_DEPLOYMENT_TARGET']='17.0'
    if args.target == 'android':
        env['CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER']=str(args.ndk.resolve()/'toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android28-clang')
    command = ['cargo','build','--release','--lib','--manifest-path',str(source/'vm/Cargo.toml')]
    if target: command += ['--target',target]
    result = subprocess.run(command,cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=300)
    (output/'build.log').write_text(result.stdout)
    if result.returncode: raise RuntimeError(f'Rust build failed; see {output}/build.log')
    library = output/'target'
    if target: library /= target
    library /= 'release/libmixer_vm.a'
    (output/'lib').mkdir()
    shutil.copyfile(library,output/'lib/libmixer_vm.a')
    digest=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    receipt={'source_revision':revision,'source_archive_sha256':hashlib.sha256(archive).hexdigest(),
        'target':target or 'host','command':command,'exit_code':0,'build_log_sha256':digest(output/'build.log'),
        'header_sha256':digest(header),'static_library_sha256':digest(output/'lib/libmixer_vm.a'),
        'rustc':subprocess.check_output(['rustc','-vV'],env=env,text=True).strip(),
        'generator_sha256':digest(Path(__file__)),
        'environment_overrides':{k:env[k] for k in ['CARGO_TARGET_DIR','IPHONEOS_DEPLOYMENT_TARGET','CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER'] if k in env},
        'qualification':'local development artifact; immutable published packaging/runtime fingerprint/signing are pending'}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'library':str(output/'lib/libmixer_vm.a'),'receipt':str(output/'receipt.json')},indent=2))


if __name__ == '__main__': main()
