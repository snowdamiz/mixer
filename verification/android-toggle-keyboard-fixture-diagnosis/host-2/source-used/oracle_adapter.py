#!/usr/bin/env python3
"""Preserve original complete-45 oracle and collector; append closed counter/setup adapters."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ORIGINAL=ROOT/'verification/android-authored-toggle-input-runner/supplement_oracle.py'
ORIGINAL_SHA256='d4010623e734c6441bd3a50105d05f0df28aef2e94c316c20298683c8db0e18d'
def sha(data):return hashlib.sha256(data).hexdigest()
def derive(kind,source=None):
    source=ORIGINAL.read_text() if source is None else source
    if sha(source.encode())!=ORIGINAL_SHA256:raise ValueError('sealed original finite oracle drift')
    marker='def validate(native, out, metadata):'
    if source.count(marker)!=1:raise ValueError('one original oracle entry point required')
    fragment=(HERE/(kind+'-oracle.fragment')).read_text()
    return source.replace(marker,'def _validate_original(native, out, metadata):',1)+fragment
def main():
    original=ORIGINAL.read_text();record={'schema':1,'originalPath':str(ORIGINAL.relative_to(ROOT)),'originalSHA256':ORIGINAL_SHA256,'unchangedOriginalRules':'entire original oracle/collector retained except private validation function name; added fields projected out and original assertion count passed to original rules','outputs':{}}
    for kind,name in [('reset-counter','reset_counter_oracle.py'),('keyboard','keyboard_oracle.py')]:
        source=derive(kind);(HERE/name).write_text(source)
        record['outputs'][name]={'sha256':sha(source.encode()),'fragmentSHA256':sha((HERE/(kind+'-oracle.fragment')).read_bytes()),'privateValidationRenameCount':1}
        (HERE/(name+'.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(keepends=True),source.splitlines(keepends=True),fromfile='sealed-original-export-oracle',tofile=name)))
    (HERE/'oracle-adaptation.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':main()
