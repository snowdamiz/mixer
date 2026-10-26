"""Select fixed-endpoint copies under unchanged caps, retaining open proof gates."""
import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(name, digest):
    p = ROOT / name
    assert sha(p) == digest
    d = json.loads(p.read_bytes())
    for m in d['members']:
        parts = PurePosixPath(m['path'])
        assert not parts.is_absolute() and '..' not in parts.parts
        f = ROOT
        for part in parts.parts:
            f /= part
            assert not f.is_symlink()
        assert f.is_file() and f.stat().st_size == m['bytes'] and sha(f) == m['sha256']
    assert len({m['path'] for m in d['members']}) == d['member_count']
    assert sum(m['bytes'] for m in d['members']) == d['member_bytes']
    return {'path':name,'sha256':digest,'members':d['member_count'],'bytes':d['member_bytes']}
proposal=verify('verification/swift-cache-state-accounting-supplement/seal.json','7558f957bfe4b8cb62703b76e064f87d2e70a535cf5d61d55b826244c6770c77')
review=verify('verification/swift-cache-state-accounting-independent-review/seal.json','706e1ab2a1caa6b14cf588d40545a086ea32fc1a7a23a7eb5c1b1f5a48dfacd8')
baseline=verify('verification/swift-cache-state-implementation/correction-1/candidate-repo-seal.json','b141dab4e6c1ecc00bd4dc50a84852ae07b31438bc0126cc724e4b47fbb8f7a6')
original=verify('verification/swift-cache-state-implementation/candidate-repo-seal.json','caceb9db9263de46ed876ff109f34eacb8fe13a9bd3ac47758f2bdac5c693ad3')
value={
 'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':sys.argv,'python':sys.version,'script_sha256':sha(Path(__file__)),
 'status':'bounded-copy-implementation-correction-selected-all-final-source-proofs-pending',
 'proposal':proposal,'independent_source_review':review,'baseline':baseline,'original_unchanged':original,
 'cost_model_disposition':'Independent review refutes the existing per-site iteration ledger under its own scalar-block model: original subtotal657 before administration; restore-only645 before administration. These are conditional source-derived bounds. The binding contract does not itself require all site-local rounding, so they are not an unconditional numeric or measured runtime overrun.',
 'selected_product_changes':[
  'Copy correction1 into new correction2 ownership; preserve every original/correction1 sealed byte and external document.',
  'Replace the two fixed scalar-commit loops (ten ROW_CELLS and two EXTRA_CELLS transfers) with12 literal-endpoint eight-byte copies derived exactly from the existing constants.',
  'Replace the twelve envelope restore iterations with12 literal-endpoint eight-byte copies using the independently checked endpoint table.',
  'Preserve transfer order, zero256-word clear, precise bytes, call/return/callback/loan/poison behavior, Q9/Q10 guard correction, public ABI and all caps. No helper or semantic change outside these copies without a separate bounded proposal.'
 ],
 'required_proofs':[
  'Independently check every literal source/destination/width/order against old formulas and derive complete source-operation partitions, without optimizer elision.',
  'Close st/sq LE-array and argument/received/store movements separately from direct copy and G3 four ld paths; no duplicate or omitted work.',
  'Give every <=16 scalar administrative block, branch predicate and copy/clear/status/return operation an exact-once source binding, with no unassigned margin transfer.',
  'Expand every complete Progress/Paid/Fixture/Option/Loan/helper/leaf/report/aggregate/Ok/Result/error source, received and drop place and simultaneous lifetime; correct macro births and verify fixed29344 role union.',
  'Requalify exact corrected source with focused transfer/cleanup/guard/fault tests, inherited78producer+14independent regressions, API default/optimized, full32 outputs and measured complete-value layouts. Preserve failures and cleanup evidence.'
 ],
 'ownership':['verification/swift-cache-state-implementation/correction-2/**'],
 'no_new_public_or_private_runtime_API':True,'no_public_state_seed_or_serializer':True,
 'G1_G7_caps':[256,2560,2568,768,640,640,248],'semantic_cap':7680,'inherited_cap':471,'preflight_cap':8192,
 'setup_cap':512,'finish_cap':256,'terminal_guard_cap':128,'role_union':29344,'reserved':41984,'global':65536,'complete_value_max':512,'Candidate_bytes':2048,
 'source_budget_proof_accepted':False,'lifetime_proof_accepted':False,'implementation_accepted':False,'native_runtime_or_capture_started':False,'GA_qualified':False,
}
p=OUT/'accounting-correction-selection.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({'path':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}))
