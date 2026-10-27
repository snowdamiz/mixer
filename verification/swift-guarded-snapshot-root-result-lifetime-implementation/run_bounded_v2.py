#!/usr/bin/env python3
"""One root-released frozen command; bounded capture and unconditional custody cleanup."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,selectors,signal,subprocess,time
P=Path(__file__).resolve().parent
R=P.parents[1]
CAP=4194304

def sha(raw):return hashlib.sha256(raw).hexdigest()
def digest(value):return sha(json.dumps(value,sort_keys=True,separators=(',',':')).encode())
def row(path,base=R):
    raw=path.read_bytes()
    return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),'bytes':len(raw),'sha256':sha(raw)}
def rows(base):return [row(path,base) for path in sorted(base.rglob('*')) if path.is_file()]
def write_once(path,value):
    with path.open('x') as output:json.dump(value,output,indent=2,sort_keys=True);output.write('\n')
def check_frozen(expected):
    assert sha((P/'source-freeze-v2.json').read_bytes())==expected,'Root-selected freeze v2 changed'
    frozen=json.loads((P/'source-freeze-v2.json').read_text())
    for member in frozen['members']:assert row(P/member['path'],P)==member,member['path']
    roster=json.loads((P/'proposed-command-roster-v2.json').read_text())
    for lane,count,key in [('vm',146,'source146_tree'),('host',11,'host11_tree')]:
        actual=rows(P/'source'/lane)
        assert len(actual)==count and digest(actual)==roster[key],lane
    for key in ['root_selection','contract_seal','frozen_correction_seal','tool']:
        member=roster[key];path=Path(member['path']);path=path if path.is_absolute() else R/path
        assert row(path)==member,key
    return roster

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('id')
    parser.add_argument('--root-compiler-lane-released',action='store_true',required=True)
    parser.add_argument('--freeze-sha',required=True)
    args=parser.parse_args()
    # No executable is started by argument parsing or command identification.
    roster=json.loads((P/'proposed-command-roster-v2.json').read_text())
    choices=[command for command in roster['commands'] if command['id']==args.id]
    assert len(choices)==1 and args.root_compiler_lane_released
    selected=choices[0];kind=selected['kind'];argv=selected['argv']
    whole_start=time.monotonic();work_deadline=whole_start+51;cleanup_deadline=whole_start+54.5
    out=P/'commands-v2'/args.id
    out.mkdir(parents=True,exist_ok=False) # Write-once evidence; never replay.
    process=None;selector=None;streams={};files={};observed={name:0 for name in ['stdout','stderr']}
    captured={name:0 for name in ['stdout','stderr']};failures=[];exception=None;phase='preflight'
    source_pins_after=False;tool_before=None;code=None;group_absent=None;child_reaped=False
    cleanup_actions=[];plan_written=False;env={};version=None
    def fail(classification,detail=None):
        item={'classification':classification}
        if detail is not None:item['detail']=str(detail)
        if item not in failures:failures.append(item)
    def remaining(deadline):return max(0.0,deadline-time.monotonic())
    def group_present():
        try:os.killpg(process.pid,0);return True
        except ProcessLookupError:return False
    def kill_owned():
        try:
            os.killpg(process.pid,signal.SIGKILL)
            if 'SIGKILL-exact-owned-group' not in cleanup_actions:cleanup_actions.append('SIGKILL-exact-owned-group')
        except ProcessLookupError:pass
        except BaseException as error:fail('cleanup-signal-failure',type(error).__name__+': '+str(error))
    def capture_ready(timeout=0.0):
        if selector is None:return False
        events=selector.select(timeout)
        for key,_mask in events:
            stream=key.fileobj;name=key.data
            try:chunk=os.read(stream.fileno(),65536)
            except BlockingIOError:continue
            if not chunk:
                selector.unregister(stream);stream.close();continue
            observed[name]+=len(chunk)
            keep=chunk[:max(0,CAP-captured[name])]
            if keep:files[name].write(keep);captured[name]+=len(keep)
            if observed[name]>CAP:fail('output-limit',name)
        return bool(events)
    def cleanup_owned():
        nonlocal code,group_absent,child_reaped
        if process is None:
            cleanup_actions.append('no-child-started');group_absent=True;return
        # This function is called from the outer finally even if poll, wait,
        # evidence writing or the postrun immutable-input check raised.
        kill_owned()
        while remaining(cleanup_deadline)>0:
            if not child_reaped:
                try:
                    code=process.wait(timeout=min(.1,remaining(cleanup_deadline)))
                    child_reaped=True
                except subprocess.TimeoutExpired:pass
                except BaseException as error:
                    fail('cleanup-wait-exception',type(error).__name__+': '+str(error))
                    # Exact-PID fallback only. Never inspect or signal another
                    # process/group, even if the Popen wait implementation fails.
                    try:
                        pid,status=os.waitpid(process.pid,os.WNOHANG)
                        if pid==process.pid:
                            code=os.waitstatus_to_exitcode(status);process.returncode=code;child_reaped=True
                    except ChildProcessError:
                        child_reaped=True;code=process.returncode
                        fail('cleanup-status-unavailable','exact child already reaped')
            group_absent=not group_present()
            if child_reaped and group_absent:break
            if not group_absent:kill_owned()
            time.sleep(min(.01,remaining(cleanup_deadline)))
        if not child_reaped:fail('cleanup-reap-incomplete')
        if not group_absent:fail('cleanup-owned-group-still-present')
        # Drain only immediately available bytes, still using the same strict
        # prefix cap. Descendants cannot keep this drain open past the deadline.
        while remaining(cleanup_deadline)>0 and capture_ready(0):pass

    try:
        try:
            assert check_frozen(args.freeze_sha)==roster
            env=dict(roster['environment']);env.update(selected.get('environment_additions',{}))
            if 'probe' in selected:assert row(Path(env['MIXER_IR02_PROBE_PATH_V1']))==selected['probe']
            executable=Path(argv[0]);tool_before=row(executable)
            if kind!='host':assert tool_before==roster['tool']
            version='exact query in this command' if kind=='version' else json.loads((P/'toolchain.json').read_text())
            plan={'schema':2,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'id':args.id,'kind':kind,
                'argv':argv,'cwd':roster['cwd'],'environment':env,'source_freeze_sha256':args.freeze_sha,
                'source_manifest':roster['source_manifest'],'source146_tree':roster['source146_tree'],'host11_tree':roster['host11_tree'],
                'root_selection':roster['root_selection'],'contract_seal':roster['contract_seal'],'base_seal':roster['frozen_correction_seal'],
                'tool':tool_before,'version':version,'parent_pid':os.getpid(),'parent_pgid':os.getpgrp(),
                'work_deadline_seconds':51,'cleanup_and_evidence_ceiling_seconds':55,'capture_bytes_each_max':CAP,
                'one_compiler_globally_root_released':True,'no_native_File_acquisition_VM_fixture_UI_capture_simulator_phone_network':True}
            write_once(out/'plan.json',plan);plan_written=True
            (P/'build').mkdir(exist_ok=True)
            for name in ['stdout','stderr']:files[name]=(out/name).open('xb')
            selector=selectors.DefaultSelector()
            if remaining(work_deadline)<=0:fail('command-deadline','preflight exhausted work deadline')
            else:
                phase='spawn'
                process=subprocess.Popen(argv,cwd=roster['cwd'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
                write_once(out/'owned-process.json',{'pid':process.pid,'pgid':process.pid,'new_session':True,'no_global_inventory':True})
                for name in ['stdout','stderr']:
                    stream=getattr(process,name);streams[name]=stream;os.set_blocking(stream.fileno(),False)
                    selector.register(stream,selectors.EVENT_READ,name)
                phase='poll-and-bounded-capture'
                while remaining(work_deadline)>0:
                    capture_ready(min(.05,remaining(work_deadline)))
                    if any(item['classification']=='output-limit' for item in failures):break
                    code=process.poll()
                    if code is not None:
                        # Collect buffered compiler output without waiting for
                        # any surviving descendant to close its pipe.
                        while remaining(work_deadline)>0 and capture_ready(0):pass
                        break
                if code is None and not failures:fail('command-deadline')
                phase='postrun-pins'
                # Includes the still-tracked child: a failure here cannot bypass
                # the outer-finally cleanup or retained final receipt.
                if remaining(work_deadline)>0:
                    assert check_frozen(args.freeze_sha)==roster
                    assert row(executable)==tool_before,'executable changed'
                    source_pins_after=True
                else:fail('postrun-pins-not-run-deadline')
        except BaseException as error:
            exception={'phase':phase,'type':type(error).__name__,'message':str(error)}
            classification={'preflight':'preflight-pin-or-plan-failure','spawn':'spawn-or-owned-record-failure',
                'poll-and-bounded-capture':'poll-or-capture-exception','postrun-pins':'postrun-pin-failure'}[phase]
            fail(classification,type(error).__name__+': '+str(error))
        finally:
            try:cleanup_owned()
            except BaseException as error:fail('cleanup-exception',type(error).__name__+': '+str(error))
    finally:
        # Receipt persistence is independent of all Popen/poll/wait/pin outcomes.
        # Even cleanup exceptions pass through this outermost evidence block.
        for stream in streams.values():
            try:stream.close()
            except BaseException as error:fail('capture-close-failure',str(error))
        if selector is not None:
            try:selector.close()
            except BaseException as error:fail('selector-close-failure',str(error))
        for output in files.values():
            try:output.close()
            except BaseException as error:fail('capture-file-close-failure',str(error))
        outputs={};diagnostic={}
        try:
            outputs={name:row(out/name) for name in ['stdout','stderr'] if (out/name).is_file()}
            diagnostic={}
            if not failures:
                if kind=='compiler-negative':
                    stderr=(out/'stderr').read_text(errors='replace')
                    codes=re.findall(r'^error\[(E\d+)\]',stderr,re.M)
                    expected=[value for value in selected['intended_diagnostics'] if re.fullmatch(r'E\d+',value)]
                    diagnostic={'intended_diagnostics':selected['intended_diagnostics'],'error_codes':codes,
                        'intended_diagnostics_found':all(value in stderr for value in selected['intended_diagnostics']),
                        'unexpected_error_codes':sorted(set(codes)-set(expected)),
                        'negative_rmeta_created':(P/'build'/(args.id+'.rmeta')).exists(),
                        'diagnostic_semantic_review':'Pending; token matching is not acceptance'}
                    if code==0:fail('negative-unexpected-success')
                    if not diagnostic['intended_diagnostics_found']:fail('negative-diagnostic-mismatch')
                    if diagnostic['unexpected_error_codes']:fail('negative-unexpected-error-code',diagnostic['unexpected_error_codes'])
                    if diagnostic['negative_rmeta_created']:fail('negative-metadata-created')
                elif code!=0:fail('unexpected-command-exit',code)
            if not failures and kind=='version':
                try:write_once(P/'toolchain.json',{'tool':roster['tool'],'version':(out/'stdout').read_text(),'SDKROOT':env['SDKROOT']})
                except BaseException as error:fail('version-receipt-failure',str(error))
        except BaseException as error:
            fail('evidence-finalization-exception',type(error).__name__+': '+str(error))
        seconds=time.monotonic()-whole_start
        if seconds>=55:fail('total-ceiling-exceeded',seconds)
        receipt={'schema':2,'id':args.id,'kind':kind,'exit':code,'seconds':seconds,'success':not failures,
            'failure_classifications':failures,'exception':exception,'plan_written':plan_written,
            'owned_pid':None if process is None else process.pid,'owned_pgid':None if process is None else process.pid,
            'child_started':process is not None,'child_reaped':child_reaped,'exact_owned_group_absent':group_absent,
            'cleanup_actions':cleanup_actions,'outputs':outputs,'observed_output_bytes':observed,'captured_output_bytes':captured,
            'captured_bytes_within_caps':all(value<=CAP for value in captured.values()),'postrun_source_and_tool_pins_verified':source_pins_after,
            'source_freeze_sha256':args.freeze_sha,'diagnostic':diagnostic,
            'no_native_File_acquisition_VM_fixture_UI_capture_simulator_phone_network_global_inventory':True}
        write_once(out/'receipt.json',receipt)
    print(json.dumps({key:receipt[key] for key in ['id','kind','exit','seconds','success','failure_classifications','exact_owned_group_absent']}))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
