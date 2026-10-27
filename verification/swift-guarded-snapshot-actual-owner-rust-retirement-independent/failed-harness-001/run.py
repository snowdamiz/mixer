"""Bounded exact owned compiler/test commands; frozen producer inputs read only."""
from pathlib import Path
import datetime,hashlib,json,os,signal,subprocess,sys,time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FROZEN=ROOT/'verification/swift-guarded-snapshot-actual-owner-rust-retirement-correction'
def sha(x):return hashlib.sha256(x).hexdigest()
def digest(x):return sha(json.dumps(x,sort_keys=True,separators=(',',':')).encode())
def row(p,base=HERE):
    b=p.read_bytes();return dict(path=str(p.relative_to(base)) if p.is_relative_to(base) else str(p),bytes=len(b),sha256=sha(b))
def rows(p):return [row(f,p) for f in sorted(p.rglob('*')) if f.is_file()]
def write(p,x):p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def frozen_inputs():
    sealed=json.loads((FROZEN/'seal.json').read_text());assert sha((FROZEN/'seal.json').read_bytes())=='46d811b1264770604106b061386e6eba01ea07e55590240eff722c36af4bcaa0'
    for m in sealed['members']:assert row(FROZEN/m['path'],FROZEN)==m
    return dict(seal=row(FROZEN/'seal.json'),members=sealed['member_count'],bytes=sealed['member_bytes'],tree=sealed['tree_sha256'])
def main():
    start=time.monotonic();assert sys.argv[2:]==['--root-compiler-lane-released']
    roster=json.loads((HERE/'proposed-command-roster.json').read_text());cmd=next(x for x in roster['commands'] if x['id']==sys.argv[1])
    out=HERE/'commands'/cmd['id'];out.mkdir(parents=True,exist_ok=False)
    (HERE/'build').mkdir(exist_ok=True)
    source_before=rows(HERE/'source');assert digest(rows(HERE/'source/vm'))==roster['source146_tree'];assert digest(rows(HERE/'source/host'))==roster['host11_tree']
    frozen_before=frozen_inputs();tool=Path(cmd['argv'][0]);tool_before=row(tool)
    if cmd['kind']=='compiler':assert tool_before['sha256']==roster['toolchain']['tool']['sha256']
    own_before=[row(HERE/n) for n in ['run.py','roster.py','prepare.py','proposed-command-roster.json','independent.inc.rs','vectors.inc.rs','independent-only.patch','frozen-oracles.json','provenance-vector-mapping.json','tested-source-manifest.json']]
    write(out/'input-before.json',dict(source=source_before,frozen=frozen_before,review_inputs=own_before))
    write(out/'plan.json',dict(schema=1,at=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=cmd,argv=cmd['argv'],cwd=str(ROOT),environment=roster['environment'],
        tool=tool_before,tool_version=roster['toolchain'],source146_tree=roster['source146_tree'],frozen_source146_tree=roster['frozen_source146_tree'],
        source_attribution='Immutable root-released candidate plus exact additive independent cfg(test) patch; no contemporaneous Git HEAD attribution.',
        root_authorization=roster['root_authorization'],total_selected_budget=dict(compiler=2,host=2),each_seconds_max=55,child_deadline=51,output_each_bytes_max=4194304,
        parent_pid=os.getpid(),parent_pgid=os.getpgrp(),python=sys.version,native_fixture_UI_capture=False))
    reason=None;cleaned=False
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        p=subprocess.Popen(cmd['argv'],cwd=ROOT,env=roster['environment'],stdout=stdout,stderr=stderr,start_new_session=True)
        while p.poll() is None:
            if time.monotonic()-start>51:reason='deadline';break
            if any((out/n).stat().st_size>4194304 for n in ['stdout','stderr']):reason='output-limit';break
            time.sleep(.05)
        if reason:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        code=p.wait(timeout=max(.1,54-(time.monotonic()-start)))
        try:os.killpg(p.pid,0);os.killpg(p.pid,signal.SIGKILL);cleaned=True
        except ProcessLookupError:pass
        while time.monotonic()-start<54:
            try:os.killpg(p.pid,0)
            except ProcessLookupError:break
            time.sleep(.05)
    try:os.killpg(p.pid,0);absent=False
    except ProcessLookupError:absent=True
    source_after=rows(HERE/'source');frozen_after=frozen_inputs();own_after=[row(HERE/n['path']) for n in own_before]
    write(out/'input-after.json',dict(source=source_after,frozen=frozen_after,review_inputs=own_after))
    result=dict(schema=1,id=cmd['id'],kind=cmd['kind'],exit=code,reason=reason,seconds=time.monotonic()-start,owned_pid=p.pid,owned_pgid=p.pid,child_reaped=p.returncode is not None,
        exact_owned_group_absent=absent,descendants_cleaned=cleaned,source_unchanged=source_before==source_after,frozen_inputs_unchanged=frozen_before==frozen_after,
        review_inputs_unchanged=own_before==own_after,tool_unchanged=tool_before==row(tool),stdout=row(out/'stdout'),stderr=row(out/'stderr'),native_fixture_UI_capture=False)
    write(out/'receipt.json',result);print(json.dumps(result))
    assert not reason and absent and result['child_reaped'] and result['source_unchanged'] and result['frozen_inputs_unchanged'] and result['review_inputs_unchanged'] and result['tool_unchanged'] and result['seconds']<=55
    assert code==0
if __name__=='__main__':main()
