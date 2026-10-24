#!/usr/bin/env python3
"""Replay the unchanged review probe with explicit finding oracles and paths."""
import datetime,difflib,hashlib,json,pathlib,subprocess,sys,time
sys.dont_write_bytecode=True
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    source=HERE/'inputs/review/name-uniqueness-probe.py';old=source.read_text();new=old
    changes=[
        ("ATTEMPT=HERE/'attempt-1'","ATTEMPT=HERE",'Harness path only: candidate and copied inputs are at this packet root.'),
        ("before=canonical(x);validate_raw(x);validate(x,expected);assert canonical(x)==before", """before=canonical(x)
        def outcome(fn):
            try:fn();return True,None
            except ValueError as exc:return False,str(exc)
        raw_admitted,raw_error=outcome(lambda:validate_raw(x));selected_admitted,selected_error=outcome(lambda:validate(x,expected))
        expected_admitted=a['relation_oid']!=b['relation_oid']
        assert raw_admitted==selected_admitted==expected_admitted
        assert canonical(x)==before""",'ACSR02: two identical relation/name pairs must now reject; different relations remain admitted.'),
        ("'raw_admitted':True,'selected_admitted':True", "'raw_admitted':raw_admitted,'selected_admitted':selected_admitted,'raw_error':raw_error,'selected_error':selected_error,'expected_admitted':expected_admitted",'Report actual corrected outcomes.'),
        ("'malformed_admission_observations':2", "'historical_malformed_now_rejected':2",'The original two admissions are preserved in inputs/review; this replay requires rejection.'),
        ("'source_digest':'7e2a24ec2aad45d07d2dd8a5d581fa8df5966e841981d20b27c75acd1de74b40'", "'source_digest':'3760cbfe5bb28407ce58d678eef22b064a960126d659df031cf11007b789d6d8'",'Bind the corrected candidate rather than mislabeling it as predecessor source.'),
        ("'scope':'model-only impossible catalog uniqueness admission; no ordinary-runtime bypass'", "'scope':'frozen review model replay; two required malformed rejections and one selected portability admission; no ordinary-runtime bypass'",'Report correction scope honestly.')]
    for before,after,reason in changes:assert new.count(before)==1,(before,new.count(before));new=new.replace(before,after)
    path=HERE/'replay-name-uniqueness.py';path.write_text(new)
    (HERE/'replay-name-uniqueness.py.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='inputs/review/name-uniqueness-probe.py',tofile='replay-name-uniqueness.py')))
    (HERE/'uniqueness-adaptations.json').write_text(json.dumps([{'before':b,'after':a,'reason':r} for b,a,r in changes],indent=2)+'\n')
    command={'argv':['python3','-B',str(path),'--out',str(HERE/'name-uniqueness-results.json')],'cwd':str(ROOT),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script_sha256':sha(path.read_bytes())};t=time.monotonic()
    p=subprocess.run(command['argv'],cwd=ROOT,capture_output=True,text=True,timeout=60);command.update(exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr,stdout_sha256=sha(p.stdout.encode()),stderr_sha256=sha(p.stderr.encode()),seconds=time.monotonic()-t)
    (HERE/'uniqueness-command.json').write_text(json.dumps(command,indent=2)+'\n');print(json.dumps(command,indent=2));return p.returncode
if __name__=='__main__':sys.exit(main())
