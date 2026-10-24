#!/usr/bin/env python3
"""Prepare only this isolated packet; preserve every predecessor byte."""
import datetime, difflib, hashlib, json, pathlib, shutil, sys
sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PRODUCER = ROOT / 'verification/hosted-authority-catalog-shape-correction'
REVIEW = ROOT / 'verification/hosted-authority-catalog-shape-review'
def sha(b): return hashlib.sha256(b).hexdigest()
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def write(path,x): path.write_text(json.dumps(x,indent=2)+'\n')
def manifest(folder):
    return [{'path':str(p.relative_to(folder)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(folder.rglob('*')) if p.is_file()]
def main():
    assert sha((PRODUCER/'receipt.json').read_bytes()) == '49ecbed394b965f68f50e242da0103005d3e86fee23a42955fc5530b982f2e22'
    assert sha((REVIEW/'receipt.json').read_bytes()) == '767f41af29131c12fdb19f72067b8ed535d271279a45324b25a0476095d0bc43'
    old_manifest=manifest(PRODUCER/'candidate')
    assert sha(canonical(old_manifest).encode()) == '7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40'
    shutil.copytree(PRODUCER/'candidate',HERE/'candidate')
    copies=[]
    def cp(source,target):
        p=ROOT/source;q=HERE/target;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
        copies.append({'path':source,'copy':target,'bytes':q.stat().st_size,'sha256':sha(q.read_bytes())})
    for rel in ['AGENTS.md','docs/hosted-catalog-wildcard-direction.md','docs/hosted-authority-catalog-shape-review.md']:
        cp(rel,'inputs/'+rel)
    for folder,name in [(PRODUCER,'producer'),(REVIEW,'review')]:
        for rel in ['receipt.json','artifact-manifest.json','check.py']:
            cp(str((folder/rel).relative_to(ROOT)),f'inputs/{name}/{rel}')
    for rel in ['boundary-tests.py','selected-expected.json','source-manifest.json','raw-field-domains.json']:
        cp(str((PRODUCER/rel).relative_to(ROOT)),'inputs/producer/'+rel)
    cp(str((PRODUCER/'selected-expected.json').relative_to(ROOT)),'selected-expected.json')
    cp(str((PRODUCER/'selected-expected.json').relative_to(ROOT)),'inputs/selected-expected.json')
    baseline='inputs/verification/hosted-authority-catalog-review/attempt-2/independent/observations/001.json.gz'
    for destination in [baseline,'inputs/'+baseline]: cp(str((PRODUCER/baseline).relative_to(ROOT)),destination)
    rel='inputs/verification/hosted-authority-catalog-review/attempt-2/domain-probes.json'
    cp(str((PRODUCER/rel).relative_to(ROOT)),rel)
    for rel in ['extra-probes.py','name-uniqueness-probe.py','name-uniqueness-observations.json','domain-review.json']:
        cp(str((REVIEW/rel).relative_to(ROOT)),'inputs/review/'+rel)
    cp(str((PRODUCER/'platform-catalog-types/catalog/pg_trigger.h').relative_to(ROOT)),'inputs/platform-catalog-types/catalog/pg_trigger.h')
    # All predecessor artifacts remain bound for honest reuse of the original
    # 128/43/5/67 runtime receipts and the prior ordinary-runtime matrix.
    for folder,name in [(PRODUCER,'producer'),(REVIEW,'review')]:
        m=json.loads((folder/'artifact-manifest.json').read_bytes())
        for entry in m['files']:
            p=ROOT/entry['path'];assert p.stat().st_size==entry['bytes'] and sha(p.read_bytes())==entry['sha256'],p
    p=HERE/'candidate/raw_validation.py';old=p.read_text();new=old
    before='        seen_oids = set()\n';after=before+'        seen_trigger_names = set()\n'
    assert new.count(before)==1;new=new.replace(before,after)
    before="            if group == 'triggers':\n";after=before+"                key = (row['relation_oid'], row['name'])\n                if key in seen_trigger_names:\n                    reject(at + ' duplicate relation/name')\n                seen_trigger_names.add(key)\n"
    assert new.count(before)==1;new=new.replace(before,after)
    before="if row[field] is None or (row[field + '_oid'] == 0) != (row[field] == '*'):"
    after="if row[field] is None or (row[field + '_oid'] == 0 and row[field] != '*'):"
    assert new.count(before)==1;new=new.replace(before,after);p.write_text(new)
    (HERE/'implementation.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='predecessor/raw_validation.py',tofile='candidate/raw_validation.py')))
    adaptations=[]
    def adapt(source,destination,replacements):
        old=(HERE/source).read_text();new=old
        for before,after,reason in replacements:
            assert new.count(before)==1,(destination,before);new=new.replace(before,after)
            adaptations.append({'script':destination,'before':before,'after':after,'reason':reason})
        (HERE/destination).write_text(new)
        (HERE/(destination+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile=source,tofile=destination)))
    adapt('inputs/producer/boundary-tests.py','replay-boundaries.py',[
        ("update({f+'_oid':o,f:v}))","update({f+'_oid':o,f:v}), raw_valid=(oid == 1 and identity == '*'))",'ACSR01: two positive-OID literal-star startup rows are valid unselected raw shapes'),
        ("probe('semantic duplicate retained '+group,duplicate,True)","probe('semantic duplicate retained '+group,duplicate,group != 'triggers')",'ACSR02: cloned trigger retains the same raw relation/name pair and is impossible even with a fresh row OID')])
    adapt('inputs/review/extra-probes.py','replay-extra-probes.py',[
        ("probe('extra semantic row retained '+group,dup,True)","probe('extra semantic row retained '+group,dup,group != 'triggers')",'ACSR02: independent extra cloned trigger must now reject raw validation')])
    write(HERE/'oracle-adaptations.json',adaptations)
    source=manifest(HERE/'candidate');write(HERE/'source-manifest.json',source)
    write(HERE/'input-manifest.json',copies)
    unchanged=[e['path'] for e in source if e['path']!='raw_validation.py']
    for rel in unchanged: assert (HERE/'candidate'/rel).read_bytes()==(PRODUCER/'candidate'/rel).read_bytes()
    write(HERE/'delta-manifest.json',{'schema':1,'modified':['raw_validation.py'],'added':[],'removed':[],'unchanged':unchanged,'upstream_source_digest':sha(canonical(old_manifest).encode()),'candidate_source_digest':sha(canonical(source).encode()),'implementation_diff_sha256':sha((HERE/'implementation.diff').read_bytes()),'scope':'Only zero-OID wildcard implication and per-relation raw trigger-name uniqueness; unchanged SQL, comparison, normalization and selected bytes.'})
    write(HERE/'preparation-command.json',{'argv':sys.argv,'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(pathlib.Path(__file__).read_bytes()),'input_bindings':len(copies),'candidate_source_digest':sha(canonical(source).encode()),'exit_code':0})
    print(canonical({'prepared':True,'input_bindings':len(copies),'candidate_source_digest':sha(canonical(source).encode())}))
if __name__=='__main__':main()
