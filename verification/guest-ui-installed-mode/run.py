#!/usr/bin/env python3
"""Rebuild the activation mode gate against frozen, retained coordinator dependencies."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OWNER = ROOT / 'verification/capability-cold-start-runtime/2026-10-23-candidate-1/receipt.json'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser(); parser.add_argument('--name', required=True); args = parser.parse_args()
assert args.name and all(c.isascii() and (c.isalnum() or c in '-_') for c in args.name)
out = HERE / args.name; out.mkdir(exist_ok=False)
work = HERE / '.build' / args.name; work.mkdir(parents=True, exist_ok=False)
snapshot = work / 'source'; owner = json.loads(OWNER.read_text())
paths = sorted((ROOT / 'capability-activation/Sources/MixerCapabilityActivation').glob('*.swift'))
paths += [ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests/GuestUIInstalledModeTests.swift', ROOT / 'capability-activation/Tests/MixerCapabilityActivationTests/CapabilityColdStartRuntimeTests.swift', ROOT / 'verification/capability-cold-start-runtime/Bundle.swift']
inputs = {}
for path in paths:
    name = path.relative_to(ROOT); target = snapshot / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target); inputs[str(name)] = sha(path)
record = {'status': 'running', 'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), 'runner_sha256':sha(Path(__file__)), 'owner_receipt_sha256':sha(OWNER), 'source_files':inputs, 'dependency_files':{}, 'commands':[], 'artifacts':{}, 'scope':'Private installed-mode classification and actual public capability facade early rejection. Rebuilt activation uses exact frozen pre-UI coordinator dependencies and native archive. No signed UI facade/exchange/bridge/presentation execution or current in-progress combined UI build is claimed.'}

def save():
    (out / 'receipt.json').write_text(json.dumps(record,indent=2)+'\n')

def run(name, command, extra=None):
    env=os.environ | {'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'} | (extra or {})
    try:
        p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=120)
        content=p.stdout+p.stderr; code=p.returncode
    except subprocess.TimeoutExpired as error:
        content=(error.stdout or b'')+(error.stderr or b'');code=124
    log=out/(name+'.log');log.write_bytes(content)
    record['commands'].append({'name':name,'command':command,'environment':{'DEVELOPER_DIR':env['DEVELOPER_DIR']} | (extra or {}),'exit_code':code,'log':str(log.relative_to(ROOT)),'log_sha256':sha(log)});save()
    if code: raise RuntimeError(name+' failed; exact log retained')
    return content.decode()

try:
    run('swift-version',['swift','--version'])
    for mode in ['debug','release','tsan']:
        old_products = Path(owner['export']).parent / mode / 'products'
        products = work / mode / 'products'; products.mkdir(parents=True)
        def adapt(command):
            return [s.replace(str(old_products),str(products)).replace(owner['export'],str(snapshot)) for s in command]
        command=adapt(next(c['command'] for c in owner['commands'] if c['name']==mode+'-module'))
        command=[s for s in command if not s.endswith('.swift')]
        command += [str(snapshot / p.relative_to(ROOT)) for p in paths if '/Sources/' in str(p)]
        for s in command:
            p=Path(s.removeprefix('-fmodule-map-file=').removeprefix('-I'))
            if p.is_absolute() and p.is_file() and not p.is_relative_to(work):record['dependency_files'][str(p)]=sha(p)
        # The linked archive selected by the frozen owner command remains exact.
        native=ROOT/'capability-activation/.build/transitions-qualified-2026-10-23-candidate-3/native/lib/libmixer_vm_capability_experimental.a'
        record['dependency_files'][str(native)]=sha(native)
        run(mode+'-module',command)
        bundle=work/mode/'ModeTests.xctest'; binary=bundle/'Contents/MacOS/ModeTests';binary.parent.mkdir(parents=True)
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable':'ModeTests','CFBundleIdentifier':'org.mixer.tests.ui-installed-mode','CFBundlePackageType':'BNDL','CFBundleVersion':'1'}))
        command=adapt(next(c['command'] for c in owner['commands'] if c['name']==mode+'-test-link'))
        command=[s for s in command if not s.endswith('.swift')];command[command.index('-o')+1]=str(binary)
        command += [str(snapshot/p.relative_to(ROOT)) for p in paths if '/Tests/' in str(p) or p.name=='Bundle.swift']
        run(mode+'-test-link',command)
        original=next(c for c in owner['commands'] if c['name']==mode+'-tests')
        output=run(mode+'-tests',[original['command'][0],str(bundle)],original['environment'])
        counts=re.findall(r'Executed (\d+) tests?, with 0 failures',output)
        assert counts and counts[-1]=='12',counts
        dylib=products/'libMixerCapabilityActivationColdStart.dylib'
        symbols=run(mode+'-native-symbols',['nm','-gU',str(dylib)])
        assert len(re.findall(r'\b_mixer_vm_capability_session_create_v1$',symbols,re.M))==1
        symbols=run(mode+'-test-symbols',['nm','-gU',str(binary)])
        assert re.search(r'\b_mixer_vm_\w+$',symbols,re.M) is None
        record['artifacts'][mode]={'tests':12,'dylib':{'path':str(dylib),'sha256':sha(dylib)},'test':{'path':str(binary),'sha256':sha(binary)}}
        print(mode+': 12 passed',flush=True)
    for name,digest in inputs.items():assert sha(ROOT/name)==sha(snapshot/name)==digest,name
    for name,digest in record['dependency_files'].items():assert sha(Path(name))==digest,name
    record['status']='12 scoped XCTest functions passed in Debug Release and TSan; frozen dependencies'
finally:
    save()
print(json.dumps({'receipt':str(out/'receipt.json'),'sha256':sha(out/'receipt.json')}))
