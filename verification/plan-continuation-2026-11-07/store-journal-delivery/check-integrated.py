#!/usr/bin/env python3
"""Root's post-application file check. Never starts a toolchain or alters source."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def require(ok, message):
    if not ok:
        raise RuntimeError(message)
def identity(path):
    b=path.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def main():
    m=json.loads((HERE/'manifest.json').read_text())
    for p,v in m['applicationChecks'].items():
        require(identity(ROOT/p)==v['after'], 'Candidate differs: '+p)
    for p,v in m['metadataEdits'].items():
        require(identity(ROOT/p)==v['after'], 'Metadata differs: '+p)
    for p,v in m['protectedBindings'].items():
        if p not in m['metadataEdits']:
            require(identity(ROOT/p)==v, 'Protected binding differs: '+p)
    spec=importlib.util.spec_from_file_location('postintegration_authority',ROOT/'scripts/ci/check-android-generated-java.py')
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
    actual=a.source_inputs(a.load_profile())
    expected=json.loads((HERE/'prospective-source103.json').read_text())
    require(actual==expected and len(actual)==103 and a.source_digest(actual)==m['proposedSourceSHA256'], 'Actual source103 differs')
    print(json.dumps({'status':'PASS_FILE_CHECKS_ONLY','sourceCount':103,'sourceSHA256':a.source_digest(actual),'toolchainsExecuted':False}))
if __name__=='__main__':
    main()
