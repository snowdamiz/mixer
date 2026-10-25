"""One-shot reproducible derivative after validating all frozen V3 bindings."""
from pathlib import Path
import difflib
import frozen_inputs as f

BASE=f.BASE
NAMES=['prepare.py','importer.py','adapter.py','test_importer.py','verify_host.py','freeze.py','auxiliary_inventory.py','test_repair.py','replay_review.py']

def main():
    before=f.verify()
    assert all(not (BASE/name).exists() for name in NAMES), 'Preserve existing derivative sources'
    assert not (BASE/'derivation-inputs.json').exists(), 'Preserve original derivation record'
    (BASE/'derivation-inputs.json').write_bytes(f.stable(before))
    patches=[]
    for name in NAMES:
        old=(f.V3/name).read_text()
        new=old.replace('runtime-v3','runtime-v4').replace('runtime_v3','runtime_v4').replace('V3','V4')
        new=new.replace('root-selection.3','root-selection.4').replace('runtime-import.3','runtime-import.4').replace('runtime-packet.3','runtime-packet.4').replace('host-receipt.3','host-receipt.4').replace('frozen-handoff.3','frozen-handoff.4').replace('native-run-v3-','native-run-v4-')
        (BASE/name).write_text(new)
        patches.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='v3/'+name,tofile='v4/'+name))
    (BASE/'namespace-adaptation.patch').write_text(''.join(patches))
    assert f.verify()==before
    print('PASS: exact frozen V3 files copied to V4 with declared namespace changes only')
if __name__=='__main__':main()
