"""Preserve initial receipts and clarify stopping between closed 64-case batches."""
import datetime
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
expected = {
    'words':'6427da586593d5ecc296580e9ff50e21634e2fb85cf5fc7cadbf846c9aecddb8',
    'transitions':'e0eb9f227e84245cfeb3dd4c66f5a03e710695f5bc621aa1c834dce21f2ab0c9',
    'sequences':'2215c2701fca5c7802e4e95ae6a7a5dc461959a8e61c9fe196fec494f7553154'}
results=[]
for kind,digest in expected.items():
    old=OUT/f'bulk-{kind}-0000-admission.json'
    assert sha(old)==digest
    value=json.loads(old.read_bytes())
    assert not (ROOT/value['review_output_directory']).exists()
    value.update({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'command':sys.argv,'python':sys.version,'script_sha256':sha(Path(__file__)),
        'supersedes_admission_sha256':digest,
        'run_sequence':'Run words, then transitions, then sequences. Complete each exact admitted64-case batch through the unchanged sealed runner, retaining all failures. Do not start the next batch if any case failed or the completed batch exited nonzero. No extra cases or expectation changes.',
        'clarification':'Initial stop phrase was ambiguous against the sealed runner. No candidate execution occurred. Root selects stopping between the three bounded batches; original receipts preserved and tooling unchanged.'})
    path=OUT/f'bulk-{kind}-0000-admission-v2.json'
    assert not path.exists()
    path.write_text(json.dumps(value,indent=2)+'\n')
    results.append({'kind':kind,'path':path.relative_to(ROOT).as_posix(),'sha256':sha(path)})
print(json.dumps(results))
