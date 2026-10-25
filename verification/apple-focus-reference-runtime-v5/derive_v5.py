"""Deterministic V4-to-V5 namespace derivation followed by the four reviewed repairs."""
import difflib
import json
from pathlib import Path
import tarfile

BASE=Path(__file__).resolve().parent
NAMES=['prepare.py','importer.py','adapter.py','test_importer.py','auxiliary_inventory.py','test_repair.py','replay_review.py','replay_v3_review.py','replay_precision.py','test_precision.py']
def namespace(text):
    text=text.replace('runtime-v4','runtime-v5').replace('runtime_v4','runtime_v5').replace('V4','V5')
    for part in ['root-selection','reference-runtime','runtime-import','runtime-packet','runtime-host-receipt','runtime-frozen-handoff']:
        text=text.replace(part+'.4',part+'.5')
    return text

def main():
    meta=json.loads((BASE/'input-bindings.json').read_bytes())
    with tarfile.open(BASE/'frozen-inputs.tar.gz','r:gz') as tar:
        originals={name:tar.extractfile('verification/apple-focus-reference-runtime-v4/'+name).read().decode() for name in NAMES}
    assert all(not (BASE/name).exists() for name in NAMES)
    adapted={name:namespace(text) for name,text in originals.items()}
    patches=[]
    for name in NAMES:
        patches.extend(difflib.unified_diff(originals[name].splitlines(True),adapted[name].splitlines(True),fromfile='frozen-v4/'+name,tofile='namespace-v5/'+name))
        (BASE/name).write_text(adapted[name])
    (BASE/'namespace-adaptation.patch').write_text(''.join(patches))
    (BASE/'namespace-sources.json').write_text(json.dumps(adapted,sort_keys=True,indent=2)+'\n')
    print('Namespace derivative written; repair patch is separately recorded after final implementation')

if __name__=='__main__':main()
