#!/usr/bin/env python3
"""Run exactly one reviewed command only after root releases this frozen lane."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,signal,subprocess,time
P=Path(__file__).resolve().parent
R=P.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(v):return sha(json.dumps(v,sort_keys=True,separators=(',',':')).encode())
def row(path,base=R):
    raw=path.read_bytes();return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def rows(base):return [row(p,base) for p in sorted(base.rglob('*')) if p.is_file()]
def write(path,v):path.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def check_frozen(expected):
    assert sha((P/'source-freeze.json').read_bytes())==expected,'Root-selected source freeze changed'
    frozen=json.loads((P/'source-freeze.json').read_text())
    for member in frozen['members']:
        assert row(P/member['path'],P)==member,member['path']
    roster=json.loads((P/'proposed-command-roster.json').read_text())
    assert len(rows(P/'source/vm'))==146
    assert digest(rows(P/'source/vm'))==roster['source146_tree']
    assert len(rows(P/'source/host'))==11
    assert digest(rows(P/'source/host'))==roster['host11_tree']
    for key in ['root_selection','contract_seal','frozen_correction_seal','tool']:
        member=roster[key];path=Path(member['path']);path=path if path.is_absolute() else R/path
        assert row(path)==member,key
    return roster

def main():
    parser=argparse.ArgumentParser();parser.add_argument('id');parser.add_argument('--root-compiler-lane-released',action='store_true',required=True);parser.add_argument('--freeze-sha',required=True)
    args=parser.parse_args();whole_start=time.monotonic()
    assert args.root_compiler_lane_released,'No compiler/host command without explicit root release'
    roster=check_frozen(args.freeze_sha)
    choices=[c for c in roster['commands'] if c['id']==args.id];assert len(choices)==1
    selected=choices[0];kind=selected['kind'];argv=selected['argv']
    out=P/'commands'/args.id;out.mkdir(parents=True,exist_ok=False) # no repeat or blind retry
    build=P/'build';build.mkdir(exist_ok=True)
    env=dict(roster['environment']);env.update(selected.get('environment_additions',{}))
    if 'probe' in selected:assert row(Path(env['MIXER_IR02_PROBE_PATH_V1']))==selected['probe']
    executable=Path(argv[0]);tool_before=row(executable)
    if kind!='host':assert tool_before==roster['tool']
    plan={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':args.id,'kind':kind,
      'argv':argv,'cwd':roster['cwd'],'environment':env,'source_freeze_sha256':args.freeze_sha,
      'source_manifest':roster['source_manifest'],'source146_tree':roster['source146_tree'],'host11_tree':roster['host11_tree'],
      'root_selection':roster['root_selection'],'contract_seal':roster['contract_seal'],'base_seal':roster['frozen_correction_seal'],
      'tool':tool_before,'version':'exact toolchain query pending' if kind=='version' else json.loads((P/'toolchain.json').read_text()),
      'parent_pid':os.getpid(),'parent_pgid':os.getpgrp(),'timeout_seconds':55,'child_deadline_seconds':51,
      'stdout_stderr_each_limit_bytes':4194304,'one_compiler_globally_root_released':True,
      'native_File_acquisition_VM_fixture_UI_capture_simulator_phone_network':False,
      'funding_shutdown_full_ownership_joint_retirement_new_prices_accepted':False}
    write(out/'plan.json',plan)
    reason=None;descendants_cleaned=False
    with (out/'stdout').open('wb') as stdout,(out/'stderr').open('wb') as stderr:
        process=subprocess.Popen(argv,cwd=roster['cwd'],env=env,stdout=stdout,stderr=stderr,start_new_session=True)
        write(out/'owned-process.json',{'pid':process.pid,'pgid':process.pid,'new_session':True,'no_global_inventory':True})
        while process.poll() is None:
            if time.monotonic()-whole_start>=51:reason='deadline';break
            if any((out/n).stat().st_size>4194304 for n in ['stdout','stderr']):reason='output-limit';break
            time.sleep(.05)
        if reason:
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        code=process.wait(timeout=max(.1,54-(time.monotonic()-whole_start)))
        try:
            os.killpg(process.pid,0)
            os.killpg(process.pid,signal.SIGKILL)
            descendants_cleaned=True
        except ProcessLookupError:pass
        while time.monotonic()-whole_start<54:
            try:os.killpg(process.pid,0)
            except ProcessLookupError:break
            time.sleep(.05)
    try:os.killpg(process.pid,0);absent=False
    except ProcessLookupError:absent=True
    check_frozen(args.freeze_sha)
    receipt={'schema':1,'id':args.id,'kind':kind,'exit':code,'reason':reason,'seconds':time.monotonic()-whole_start,
      'owned_pid':process.pid,'owned_pgid':process.pid,'child_reaped':process.returncode is not None,
      'exact_owned_group_absent':absent,'descendants_cleaned':descendants_cleaned,
      'stdout':row(out/'stdout'),'stderr':row(out/'stderr'),'source_and_inputs_unchanged':True,
      'tool_unchanged':row(executable)==tool_before,'output_within_caps':all((out/n).stat().st_size<=4194304 for n in ['stdout','stderr']),
      'no_native_File_acquisition_VM_fixture_UI_capture_simulator_phone_network':True}
    if kind=='compiler-negative':
        stderr=(out/'stderr').read_text()
        codes=re.findall(r'^error\[(E\d+)\]',stderr,re.M)
        expected=[d for d in selected['intended_diagnostics'] if re.fullmatch(r'E\d+',d)]
        receipt.update({'intended_diagnostics':selected['intended_diagnostics'],
          'intended_diagnostics_found':all(d in stderr for d in selected['intended_diagnostics']),
          'error_codes':codes,'unexpected_error_codes':sorted(set(codes)-set(expected)),
          'negative_rmeta_created':(build/(args.id+'.rmeta')).exists(),
          'diagnostic_semantic_review':'Pending; token matching alone is not acceptance'})
    write(out/'receipt.json',receipt)
    assert reason is None and absent and receipt['child_reaped'] and receipt['tool_unchanged'] and receipt['output_within_caps'] and receipt['seconds']<=55,receipt
    if kind=='version':
        assert code==0
        write(P/'toolchain.json',{'tool':roster['tool'],'version':(out/'stdout').read_text(),'SDKROOT':env['SDKROOT']})
    elif kind=='compiler-negative':
        assert code!=0 and receipt['intended_diagnostics_found'] and not receipt['unexpected_error_codes'] and not receipt['negative_rmeta_created'],receipt
    else:assert code==0,receipt
    print(json.dumps({key:receipt[key] for key in ['id','kind','exit','seconds','exact_owned_group_absent']}))
if __name__=='__main__':main()
