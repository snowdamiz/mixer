"""One independent bounded host case per process, with unresolved states intact."""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "replay/corrected/replay"))
import prototype as p
import test_preparation as t

def refused(call):
    try: call()
    except p.Refusal as error: return error.code
    raise AssertionError("required refusal was not observed")

def lifecycle(directory):
    paths,sizes,head,_ = t.fixture(directory)
    with ExitStack() as stack:
        inputs = [stack.enter_context(p.Retained(paths[k],sizes[k])) for k in p.NAMES[:7]]
        stale = p.Retained(paths[p.NAMES[7]],p.BODY)
        old_access,old_generation = stale.fd,stale.generation
        report = stale.close()
        with p.Retained(paths[p.NAMES[7]],p.BODY) as fresh:
            assert old_access.saved_number == fresh.fd.saved_number and old_generation != fresh.generation
            operations = [stale.check, lambda:stale.seek(0), lambda:p.IO().read(old_access,memoryview(bytearray(1))), lambda:os.fstat(old_access), lambda:p.child_lease(stale).__enter__(), lambda:p.compose_from_retained_fixture(inputs+[stale],head,directory/"refused",directory)]
            refusals = [refused(operation) for operation in operations]
            assert not (directory/"refused").exists()
            assert stale.close() is report
            assert p.hash_range(fresh,bytearray(4096),p.IOCount(),p.IO()) == hashlib.sha256(bytes([93])*p.BODY).digest()
    assert p.ownership_snapshot()["healthy_zero"]
    return {"case":"lifecycle", "natural_number_reuse":True,"new_generation":True,"refusals":refusals,"real_retained_entry_refused":True}

def multi_close(directory):
    path=directory/"file";path.write_bytes(b"x")
    held=p.Retained(path,1)
    tokens=tuple(held._tokens);numbers=tuple(reversed(held.fds))
    original=os.close;calls=[];pre=OSError("independent before syscall");post=OSError("independent after syscall")
    def boundary(number):
        index=len(calls);calls.append(number)
        if index==0:raise pre
        original(number)
        if index==len(numbers)-1:raise post
    with patch.object(p.os,"close",boundary):
        try:held.close()
        except p.CleanupFailure as error:caught=error
        else:raise AssertionError("close faults hidden")
        before=len(calls)
        try:held.close()
        except p.CleanupFailure as second:assert second.report is caught.report
        else:raise AssertionError("terminal uncertainty hidden")
        assert len(calls)==before
    assert calls==list(numbers)
    assert {id(f.exception) for f in caught.failures}=={id(pre),id(post)}
    os.fstat(numbers[0])
    for number in numbers[1:]:
        try:os.fstat(number)
        except OSError:pass
        else:raise AssertionError("independent close stranded")
    assert len(p.TOKENS)==len(p.UNCERTAIN_CLOSES)==2 and not p.ownership_snapshot()["healthy_zero"]
    assert numbers[0] in p.OPEN_FDS and numbers[-1] in p.OPEN_FDS
    assert refused(lambda:p.Retained(path,1))=="owner-admission-quarantined-or-full"
    return {"case":"multi-close","attempts":len(calls),"uncertain":2,"all_independent_closes_attempted_once":True,"original_exception_identities_preserved":True,"numeric_retry":False}

def nested_primary(directory, completed):
    path=directory/"file";path.write_bytes(b"x")
    original=os.close;calls=[];injected=[]
    primary=ValueError("independent original operation failure")
    result={"independent_completed_observation":True}
    def boundary(number):
        # Only authored retained closes, never TemporaryDirectory internals.
        if not any(x.number==number and x.state=="closing" for x in p.TOKENS.values()):return original(number)
        calls.append(number)
        if len(injected)<2:
            fault=OSError("independent cleanup fault "+str(len(injected)));injected.append(fault)
            if len(injected)==1:original(number)
            raise fault
        return original(number)
    try:
        with patch.object(p.os,"close",boundary):
            with p.CleanupFrame() as outer:
                outer.adopt(p.Retained(path,1))
                with p.CleanupFrame() as inner:
                    inner.adopt(p.Retained(path,1))
                    if completed:inner.result=result
                    else:raise primary
    except p.CleanupAggregate as error:caught=error
    else:raise AssertionError("cleanup result suppressed")
    assert caught.primary is (None if completed else primary)
    assert caught.retained_result is (result if completed else None)
    faults=[f for e in caught.cleanup_errors if isinstance(e,p.CleanupFailure) for f in e.failures]
    assert {id(f.exception) for f in faults}=={id(e) for e in injected}
    assert len(calls)==len(set(calls)) and len(p.UNCERTAIN_CLOSES)==2
    return {"case":"nested-result" if completed else "nested-primary","primary_identity":caught.primary is primary,"completed_result_identity":caught.retained_result is result,"cleanup_errors":len(faults),"calls_once":True}

def number_reuse(directory):
    path=directory/"file";path.write_bytes(b"preserve fresh owner")
    held=p.Retained(path,path.stat().st_size);target=held.fd.saved_number
    original=os.close;first=True
    def post(number):
        nonlocal first
        original(number)
        if first:first=False;raise OSError("independent known post-close reporting fault")
    with patch.object(p.os,"close",post):
        try:held.close()
        except p.CleanupFailure as error:caught=error
        else:raise AssertionError("fault hidden")
    probes=[]
    try:
        for _ in range(65):
            number=os.open(path,os.O_RDONLY);probes.append(number)
            if number==target:break
        assert probes[-1]==target
        with patch.object(p.os,"close",side_effect=AssertionError("blind old close retry")):
            try:held.close()
            except p.CleanupFailure as second:assert second.report is caught.report
            else:raise AssertionError("quarantine hidden")
        assert os.read(probes[-1],128)==b"preserve fresh owner"
        assert len(p.UNCERTAIN_CLOSES)==1
    finally:
        for number in reversed(probes):original(number)
    return {"case":"number-reuse","new_test_owners":len(probes),"old_close_calls_after_reuse":0,"fresh_owner_usable":True,"uncertainty_preserved":True}

def stdio_close(directory):
    original=tempfile.TemporaryFile;streams=[]
    primary=p.Refusal("independent-child-failure","terminal-reap")
    fault=OSError("independent stdio pre-close error")
    class Stream:
        def __init__(self,*args,**kwargs):
            self.real=original(*args,**kwargs);self.index=len(streams);streams.append(self)
        def __enter__(self):return self
        def __getattr__(self,name):return getattr(self.real,name)
        def __exit__(self,*args):
            if self.index==1:raise fault
            self.real.close()
    try:
        with patch.object(p.tempfile,"TemporaryFile",Stream):
            with p.terminal_streams(directory):raise primary
    except BaseException as error:caught=error
    else:raise AssertionError("operation unexpectedly passed")
    saved=streams[1].real.fileno()
    os.fstat(saved)
    snapshot=p.ownership_snapshot()
    observation={"case":"stdio-close","injected_error_raised_before_actual_stream_close":True,"known_owned_stream_remains_open":True,"stream_registry_count":len(p.STDIO_FDS),"snapshot":snapshot,"primary_is_preserved_as_aggregate_primary":isinstance(caught,p.CleanupAggregate) and caught.primary is primary,"raised_exception_type":type(caught).__name__,"raised_exception_is_stdio_fault":caught is fault,"original_primary_in_context_chain":caught.__context__ is primary,"actual_OS_ambiguity_resolved":False}
    print(json.dumps(observation,sort_keys=True),flush=True)
    assert not snapshot["healthy_zero"], "known open terminal stream cannot disappear behind healthy_zero=true"
    assert isinstance(caught,p.CleanupAggregate) and caught.primary is primary, "terminal cleanup cannot replace the original failure as primary"
    return observation

def main():
    assert len(sys.argv)==2
    scratch=ROOT/"owned-scratch";scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="review-",dir=scratch) as name:
        directory=Path(name)
        if sys.argv[1]=="lifecycle":result=lifecycle(directory)
        elif sys.argv[1]=="multi-close":result=multi_close(directory)
        elif sys.argv[1]=="nested-primary":result=nested_primary(directory,False)
        elif sys.argv[1]=="nested-result":result=nested_primary(directory,True)
        elif sys.argv[1]=="number-reuse":result=number_reuse(directory)
        elif sys.argv[1]=="stdio-close":result=stdio_close(directory)
        else:raise ValueError("closed case")
        result["ownership_at_process_exit"]=p.ownership_snapshot()
        result["synthetic_unresolved_state_not_healthy_cleanup"]=not p.ownership_snapshot()["healthy_zero"]
        result["actual_OS_ambiguous_close_resolution"]=False
        print(json.dumps(result,sort_keys=True),flush=True)

if __name__=="__main__":main()
