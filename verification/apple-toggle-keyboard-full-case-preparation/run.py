#!/usr/bin/env python3
"""Read-only sealed preparation verification. No runtime module is imported."""
import argparse
import hashlib
import json
import pathlib
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[1]
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
read=lambda path:json.loads(path.read_bytes())
def require(value,message):
    if not value:raise ValueError(message)
def verify(unsealed=False):
    seal_path=BASE/'packet-seal.json'
    if not unsealed:
        seal=read(seal_path)
        require(seal['schema']=='mixer.apple-toggle.keyboard-full-case-preparation.1','Wrong preparation seal')
        for name,digest in seal['files'].items():
            path=ROOT/name
            require(path.is_file() and not path.is_symlink() and sha(path)==digest,'Sealed preparation changed: '+name)
        for name,digest in read(BASE/'input-bindings.json').items():
            path=pathlib.Path(name) if name.startswith('/') else ROOT/name
            require(path.is_file() and sha(path)==digest,'Bound input changed: '+name)
        controls=read(BASE/'host-controls.json')
        require(controls['passed'] is True,'Host controls incomplete')
        for name,digest in controls['sourceFiles'].items():require(sha(ROOT/name)==digest,'Host control source changed: '+name)
    return dict(schema='mixer.apple-toggle.keyboard-full-case-preflight.1',status='sealed-preparation-only' if not unsealed else 'unsealed-host-control-only',
      sealSHA256=sha(seal_path) if seal_path.is_file() and not unsealed else None,expectedXCTestMethods=7,applicationCasesExecuted=0,
      applicationCasesUnrun=['keyboard-disabled-off','keyboard-disabled-on','keyboard-enabled-off','keyboard-enabled-on','keyboard-stale-off','keyboard-stale-on'],
      nativeInstancesQueried=False,nativeExecution=False,runnerCompiled=False,nativeAcceptancePending=True,
      nativeKeyboardQualification=False,carrierAccepted=False,physicalPhones='disconnected-deferred',gaAccepted=False)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify']);parser.add_argument('--unsealed-host-check',action='store_true');args=parser.parse_args()
    print(json.dumps(verify(args.unsealed_host_check),sort_keys=True))
