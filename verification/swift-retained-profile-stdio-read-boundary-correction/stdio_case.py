"""Contained stdio lifecycle witnesses; no uncertain-number retirement/retry."""
import gc
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
import weakref
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"new/replay/corrected/replay"))
import prototype as p
import test_preparation as t


def refused(call):
    try:call()
    except p.Refusal as error:return error.code
    raise AssertionError("required refusal not observed")


def failures(error):
    output=[]
    for cleanup in error.cleanup_errors:
        assert isinstance(cleanup,p.CleanupFailure)
        for fault in cleanup.failures:
            output.append({"resource":fault.resource_kind,"owner_generation":fault.owner_generation,"token_generation":fault.token_generation,"saved_number_observation":fault.saved_number,"exception_type":type(fault.exception).__name__,"exception_text":str(fault.exception),"raw_traceback":traceback.format_exception(fault.exception,chain=False)})
    return output


def gates(owner):
    return [refused(owner.fileno),refused(lambda:owner.seek(0)),refused(lambda:owner.read(1))]


def primary_record(error):
    if error is None:return None
    return {"type":type(error).__name__,"text":str(error),"code":getattr(error,"code",None),"stage":getattr(error,"stage",None),"raw_traceback":traceback.format_exception(error,chain=False)}


def healthy(directory):
    observed={"complete":True}
    with p.terminal_streams(directory) as first:
        old=tuple(first);numbers=[x.fileno() for x in old]
        assert all(not isinstance(x,io.IOBase) and "__del__" not in type(x).__dict__ for x in old)
        os.write(old[0].fileno(),b"abc");old[0].seek(0);assert old[0].read(512)==b"abc"
        first.completed(observed)
    reports=[x._report for x in old]
    assert p.ownership_snapshot()["healthy_zero"]
    with p.terminal_streams(directory) as fresh:
        assert [x.fileno() for x in fresh]==numbers
        refs=[weakref.ref(x) for x in old]
        calls=[];original=p._stdio_close_syscall
        def spy(number):calls.append(number);return original(number)
        with patch.object(p,"_stdio_close_syscall",spy):
            for owner,report in zip(old,reports):
                assert owner.close() is report
                gates(owner)
            first.__exit__(None,None,None)
            del owner,old,first
            gc.collect()
            assert all(ref() is None for ref in refs)
            assert calls==[]
        os.write(fresh.out.fileno(),b"new");fresh.out.seek(0);assert fresh.out.read(3)==b"new"
    assert p.ownership_snapshot()["healthy_zero"]
    return {"case":"healthy-reuse-gc","natural_number_reuse":True,"old_owners_collected":True,"automatic_close_calls_after_collection":0,"fresh_owners_usable":True,"owning_python_stream_objects":0,"cleanup_kind":"healthy-zero"}


def close_fault(directory,pattern,kind):
    primary=p.Refusal("original-stdio-body-failure","terminal-reap")
    result={"completed-observation":True};owners=[];calls=[];injected=[]
    original_prepare=p._stdio_prepare;original_close=p._stdio_close_syscall
    def prepare(owner):owners.append(owner);return original_prepare(owner)
    def boundary(number):
        index=next(i for i,x in enumerate(owners) if x._token.number==number)
        calls.append(index)
        gates(owners[index])
        mode=pattern[index]
        if mode=="-":return original_close(number)
        error=OSError("stdio "+mode+" stream "+str(index));injected.append(error)
        if mode=="q":original_close(number)
        raise error
    with patch.object(p,"_stdio_prepare",prepare),patch.object(p,"_stdio_close_syscall",boundary):
        try:
            with p.terminal_streams(directory) as bundle:
                if kind in ("result","both"):bundle.completed(result)
                if kind in ("primary","both"):raise primary
        except p.CleanupAggregate as error:caught=error
        else:raise AssertionError("stdio close failure suppressed")
        before=len(calls)
        try:bundle.__exit__(None,None,None)
        except p.CleanupAggregate as again:assert again is caught
        else:raise AssertionError("terminal bundle failure hidden")
        for owner in owners:
            if owner.state=="quarantined":
                try:owner.close()
                except p.CleanupFailure as error:assert error.report is owner._report
                else:raise AssertionError("quarantine hidden")
            else:owner.close()
        assert len(calls)==before
    assert calls==[1,0] and len(owners)==2
    assert caught.primary is (None if kind=="result" else primary)
    assert caught.retained_result is (None if kind=="primary" else result)
    actual=[f for cleanup in caught.cleanup_errors for f in cleanup.failures]
    assert {id(f.exception) for f in actual}=={id(x) for x in injected}
    expected=sum(x!="-" for x in pattern)
    state=p.ownership_snapshot();assert state["stdio_uncertain_close_records"]==expected and not state["healthy_zero"]
    assert state["stdio_token_states"]=={"acquiring":0,"owned":0,"closing":0,"uncertain":expected}
    assert refused(lambda:p.RawStdio(directory))=="stdio-admission-quarantined-or-full"
    known_open=0
    for index,owner in enumerate(owners):
        number=owner._token.number
        try:os.fstat(number)
        except OSError:assert pattern[index] in ("-","q")
        else:assert pattern[index]=="p";known_open+=1
        gates(owner)
    return {"case":"close-fault","pattern":pattern,"body":kind,"close_order":calls,"all_independent_streams_attempted":True,"known_open_by_controlled_preclose_oracle":known_open,"primary_identity":caught.primary is primary,"original_primary":primary_record(caught.primary),"completed_result_identity":caught.retained_result is result,"retained_result":caught.retained_result,"cleanup_failures":failures(caught),"uncertain_saved_numbers_retried":False,"owning_python_stream_objects":0,"cleanup_kind":"synthetic-uncertainty-retained"}


def acquisition(directory,index,stage,close_mode):
    original=p._stdio_acquire;prepare_original=p._stdio_prepare;close_original=p._stdio_close_syscall;unlink_original=os.unlink
    primary=OSError("original "+stage+" acquisition "+str(index));acquired=[];owners=[];calls=[];close_error=OSError("first-stream cleanup "+close_mode)
    attempts=0
    def acquire(owner,scratch):
        nonlocal attempts
        current=attempts;attempts+=1
        if current==index and stage=="before":raise primary
        original(owner,scratch);acquired.append(owner._token.number)
        if current==index and stage=="post-acquire":raise primary
    def prepare(owner):
        current=len(owners);owners.append(owner)
        if current==index and stage=="pre-prepare":raise primary
        prepare_original(owner)
        if current==index and stage=="post-prepare":raise primary
    unlink_count=0
    def unlink(path,*args,**kwargs):
        nonlocal unlink_count
        if Path(path).name.startswith(".mixer-stdio-"):
            current=unlink_count;unlink_count+=1
            if current==index and stage=="unlink-pre":raise primary
            result=unlink_original(path,*args,**kwargs)
            if current==index and stage=="unlink-post":raise primary
            return result
        return unlink_original(path,*args,**kwargs)
    def close(number):
        calls.append(number)
        if acquired and number==acquired[0] and close_mode!="-":
            if close_mode=="q":close_original(number)
            raise close_error
        return close_original(number)
    with patch.object(p,"_stdio_acquire",acquire),patch.object(p,"_stdio_prepare",prepare),patch.object(p,"_stdio_close_syscall",close),patch.object(p.os,"unlink",unlink):
        try:
            with p.terminal_streams(directory):raise AssertionError("acquisition unexpectedly completed")
        except BaseException as error:caught=error
    actual_primary=caught.primary if isinstance(caught,p.CleanupAggregate) else caught
    assert actual_primary is primary
    assert attempts==index+1 and len(calls)==len(set(calls))==len(acquired)
    assert all(x._report is not None for x in owners)
    path_pending=stage in ("post-acquire","pre-prepare","unlink-pre","unlink-post")
    state=p.ownership_snapshot()
    assert state["stdio_path_obligations"]==int(path_pending)
    assert state["stdio_uncertain_close_records"]==int(close_mode!="-")
    assert state["healthy_zero"] is not (path_pending or close_mode!="-")
    return {"case":"acquisition","stream_index":index,"stage":stage,"first_stream_cleanup_mode":close_mode,"acquisition_attempts":attempts,"successful_raw_acquisitions":len(acquired),"close_attempts":len(calls),"original_primary_identity":True,"original_primary":primary_record(actual_primary),"path_obligations":state["stdio_path_obligations"],"cleanup_failures":failures(caught) if isinstance(caught,p.CleanupAggregate) else [],"uncertain_saved_numbers_retried":False,"cleanup_kind":"synthetic-uncertainty-retained" if not state["healthy_zero"] else "healthy-zero"}


def reuse_uncertain(directory):
    original=p._stdio_close_syscall;owners=[]
    original_prepare=p._stdio_prepare
    def prepare(owner):owners.append(owner);return original_prepare(owner)
    fault=OSError("known post-close reuse signal")
    def boundary(number):
        original(number)
        if number==owners[1]._token.number:raise fault
    with patch.object(p,"_stdio_prepare",prepare),patch.object(p,"_stdio_close_syscall",boundary):
        try:
            with p.terminal_streams(directory):pass
        except p.CleanupAggregate as caught:report=caught
        else:raise AssertionError("fault hidden")
    target=owners[1]._token.number
    file=directory/"fresh";file.write_bytes(b"fresh owner")
    fresh=[]
    try:
        for _ in range(8):
            number=os.open(file,os.O_RDONLY);fresh.append(number)
            if number==target:break
        assert fresh[-1]==target
        with patch.object(p,"_stdio_close_syscall",side_effect=AssertionError("uncertain close retry")):
            try:owners[1].close()
            except p.CleanupFailure:pass
            else:raise AssertionError("quarantine hidden")
            gc.collect()
        assert os.read(fresh[-1],32)==b"fresh owner"
        assert not isinstance(owners[1],io.IOBase) and "__del__" not in type(owners[1]).__dict__
    finally:
        for number in reversed(fresh):os.close(number)
    assert p.ownership_snapshot()["stdio_uncertain_close_records"]==1
    return {"case":"uncertain-reuse-gc","natural_number_reuse":True,"fresh_owner_usable":True,"uncertain_close_retries":0,"automatic_file_destructor_present":False,"original_exception_identity":report.cleanup_errors[0].failures[0].exception is fault,"cleanup_kind":"synthetic-uncertainty-retained"}


def actual_child(directory,primary_mode,mixed):
    paths,sizes,head,_=t.fixture(directory)
    owners=[];original_prepare=p._stdio_prepare;original_close=p._stdio_close_syscall;original_complete=p.TerminalStreams.completed;original_os_close=os.close
    primary=p.Refusal("original-after-terminal-child","child-report");complete=[];injected=[];calls=[];retained_fault=OSError("retained close alongside stdio")
    def prepare(owner):owners.append(owner);return original_prepare(owner)
    def completed(bundle,value):
        complete.append(value)
        if primary_mode:raise primary
        return original_complete(bundle,value)
    def boundary(number):
        calls.append(number);error=OSError("terminal fixed-child stdio close");injected.append(error)
        if number==owners[0]._token.number:original_close(number)
        raise error
    used=False
    def retained_boundary(number):
        nonlocal used
        if mixed and not used and any(t.number==number and t.state=="closing" for t in p.TOKENS.values()):
            used=True;raise retained_fault
        return original_os_close(number)
    with patch.object(p,"_stdio_prepare",prepare),patch.object(p,"_stdio_close_syscall",boundary),patch.object(p.TerminalStreams,"completed",completed),patch.object(p.os,"close",retained_boundary):
        try:p.compose_fixture(paths,sizes,head,directory/"profile",directory)
        except p.CleanupAggregate as error:caught=error
        else:raise AssertionError("stdio faults suppressed")
    assert len(complete)==1 and complete[0][1]["terminal_reaped"]
    assert caught.primary is (primary if primary_mode else None)
    assert caught.retained_result is (None if primary_mode else complete[0])
    allfaults=[f for e in caught.cleanup_errors for f in e.failures]
    expected=injected+([retained_fault] if mixed else [])
    assert {id(f.exception) for f in allfaults}=={id(e) for e in expected}
    assert len(calls)==2 and p.ownership_snapshot()["stdio_uncertain_close_records"]==2
    return {"case":"actual-terminal-child","primary_mode":primary_mode,"mixed_retained_cleanup":mixed,"fixed_child_terminal_reaped":True,"child_completed_observation":complete[0],"original_primary_identity":caught.primary is primary,"original_primary":primary_record(caught.primary),"completed_result_identity":caught.retained_result is complete[0],"cleanup_failures":failures(caught),"cleanup_kind":"synthetic-uncertainty-retained"}


def main(argv):
    scratch=ROOT/"owned-scratch";scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stdio-case-",dir=scratch) as name:
        directory=Path(name)
        if argv[1:]==["healthy"]:result=healthy(directory)
        elif len(argv)==4 and argv[1]=="close" and argv[2] in ("p-","q-","-p","-q","pp","pq","qp","qq") and argv[3] in ("primary","result","both"):result=close_fault(directory,argv[2],argv[3])
        elif len(argv)==5 and argv[1]=="acquire" and argv[2] in ("0","1") and argv[3] in ("before","post-acquire","pre-prepare","post-prepare","unlink-pre","unlink-post") and argv[4] in ("-","p","q"):result=acquisition(directory,int(argv[2]),argv[3],argv[4])
        elif argv[1:]==["reuse-uncertain"]:result=reuse_uncertain(directory)
        elif len(argv)==4 and argv[1]=="child" and argv[2] in ("primary","result") and argv[3] in ("mixed","stdio"):result=actual_child(directory,argv[2]=="primary",argv[3]=="mixed")
        else:raise ValueError("closed stdio case argv")
        result["ownership_before_directory_cleanup"]=p.ownership_snapshot()
    result["ownership_at_process_exit"]=p.ownership_snapshot()
    result["real_OS_ambiguity_resolved"]=False
    result["process_containment_is_not_healthy_cleanup"]=True
    result["authority"]=dict(real_binding=False,runtime=False,ota=False,ga=False)
    print(json.dumps(result,sort_keys=True,separators=(",",":")))


if __name__=="__main__":main(sys.argv)
