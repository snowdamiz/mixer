"""One bounded host fault case per process; uncertain numbers are never retried.

Known pre/post syscall fates are test-oracle observations only. The production
model retains uncertainty and has no resolution API; process exit contains these
synthetic cases without claiming that a real ambiguous close was successful.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "corrected" / "replay"))
import prototype as p
import test_preparation as t


def refused(function):
    try:
        function()
    except p.Refusal as error:
        return error.code
    raise AssertionError("stale access accepted")


def deep_file(directory):
    # Make exactly64 path components and65 owned fds, including root.
    parts = len(directory.parts) - 1
    target = directory
    for i in range(63 - parts):
        target = target / ("d" + str(i))
        target.mkdir()
    target = target / "file"
    target.write_bytes(b"unchanged quiescent bytes")
    assert len(target.parts) - 1 == 64
    return target


def summary(error):
    failures = []
    errors = error.cleanup_errors if isinstance(error, p.CleanupAggregate) else (error,)
    for item in errors:
        if isinstance(item, p.CleanupFailure):
            for f in item.failures:
                failures.append({"owner_generation":f.owner_generation,"token_generation":f.token_generation,"saved_number_observation":f.saved_number,"exception_type":type(f.exception).__name__,"exception_text":str(f.exception)[:256],"raw_exception_traceback":traceback.format_exception(f.exception,chain=False)})
        else:
            failures.append({"cleanup_error_type":type(item).__name__,"code":getattr(item,"code",None)})
    return failures


def close_position(directory, mode, position):
    path = deep_file(directory)
    held = p.Retained(path, path.stat().st_size)
    numbers = tuple(held.fds)
    tokens = tuple(held._tokens)
    assert len(numbers) == 65
    order = tuple(reversed(numbers))
    original = os.close
    calls, physically_closed = [], []
    injected = OSError("synthetic " + mode + " at owned position " + str(position))
    def boundary(fd):
        index = len(calls)
        calls.append(fd)
        assert held.state == "closing"
        if index == position and mode == "pre":
            raise injected
        original(fd)
        physically_closed.append(fd)
        if index == position and mode == "post":
            raise injected
    with patch.object(p.os, "close", boundary):
        try:
            held.close()
        except p.CleanupFailure as error:
            caught = error
        else:
            raise AssertionError("close fault suppressed")
        before_repeat = len(calls)
        try:
            held.close()
        except p.CleanupFailure as second:
            assert second.report is caught.report
        else:
            raise AssertionError("quarantine silently became healthy")
        assert len(calls) == before_repeat
    assert calls == list(order), "all independent owned close calls must run once"
    assert len(caught.failures) == 1 and caught.failures[0].exception is injected
    assert held.state == "quarantined" and held.fds == []
    assert len(p.TOKENS) == len(p.UNCERTAIN_CLOSES) == 1
    assert caught.report.closed_generations == tuple(x.generation for x in reversed(tokens) if x.number != order[position])
    assert order[position] in p.OPEN_FDS
    assert not p.ownership_snapshot()["healthy_zero"]
    assert refused(lambda:p.OPEN_FDS.clear()) == "accounting-view-read-only"
    assert len(p.UNCERTAIN_CLOSES) == 1
    # Keep the original R02 behavioral assertions: no remaining independent
    # ancestor is stranded; a known pre-syscall unclosed leaf remains accounted.
    for fd in order:
        if fd == order[position] and mode == "pre":
            os.fstat(fd)  # Separate controlled oracle; no new fd has opened.
        else:
            try: os.fstat(fd)
            except OSError: pass
            else: raise AssertionError("independently owned descriptor stranded")
    checks = [refused(lambda:held.check()), refused(lambda:p.hash_range(held,bytearray(4096),p.IOCount(),p.IO())), refused(lambda:held.seek(0)), refused(lambda:held.readinto(memoryview(bytearray(1)))), refused(lambda:os.fstat(held.fd)), refused(lambda:p.child_lease(held).__enter__())]
    assert refused(lambda:p.Retained(path,path.stat().st_size)) == "owner-admission-quarantined-or-full"
    return {"case":"close-position","mode":mode,"position":position,"owned_positions":65,"attempted_once":len(calls),"independent_remaining_closed":64,"synthetic_physically_closed_by_oracle":len(physically_closed),"original_close_exception_preserved":True,"idempotent_repeat_additional_syscalls":0,"stale_access_refusals":checks,"failures":summary(caught),"cleanup_kind":"synthetic-known-fault; terminal uncertainty retained","uncertain_saved_numbers_retried":False}


def stale_reuse(directory):
    paths,sizes,head,_ = t.fixture(directory)
    checks = {}
    with ExitStack() as stack:
        inputs=[stack.enter_context(p.Retained(paths[k],sizes[k])) for k in p.NAMES[:7]]
        stale=p.Retained(paths[p.NAMES[7]],p.BODY)
        saved=stale.fd
        saved_generation=stale.generation
        report=stale.close()
        assert report.terminal_state == "closed"
        with p.Retained(paths[p.NAMES[7]],p.BODY) as fresh:
            assert saved == fresh.fd
            assert saved_generation != fresh.generation
            before=p.ownership_snapshot()
            checks["check"]=refused(stale.check)
            checks["hash"]=refused(lambda:p.hash_range(stale,bytearray(4096),p.IOCount(),p.IO()))
            checks["read"]=refused(lambda:stale.readinto(memoryview(bytearray(1))))
            checks["seek"]=refused(lambda:stale.seek(0))
            checks["raw_borrow_read"]=refused(lambda:p.IO().read(saved,memoryview(bytearray(1))))
            checks["raw_borrow_seek"]=refused(lambda:os.lseek(saved,0,os.SEEK_SET))
            checks["borrow_metadata"]=refused(lambda:os.fstat(saved))
            checks["lease"]=refused(lambda:p.child_lease(stale).__enter__())
            checks["adopt"]=refused(lambda:p.child_lease(stale).claim_launch())
            out=directory/"must-not-create"
            checks["real_retained_entry"]=refused(lambda:p.compose_from_retained_fixture(inputs+[stale],head,out,directory))
            assert not out.exists()
            original=os.close
            calls=[]
            def observed(fd):
                calls.append(fd)
                return original(fd)
            with patch.object(p.os,"close",observed):
                assert stale.close() is report
            assert calls == []
            assert p.ownership_snapshot() == before
            actual=p.hash_range(fresh,bytearray(4096),p.IOCount(),p.IO())
            assert actual==hashlib.sha256(bytes([93])*p.BODY).digest()
    assert p.ownership_snapshot()["healthy_zero"]
    return {"case":"stale-reuse","same_descriptor_number":True,"distinct_owner_generation":True,"same_inode_path":True,"stale_close_extra_syscalls":0,"fresh_owner_usable":True,"checks":checks,"real_retained_entry_used":True,"cleanup_kind":"healthy-zero"}


def closing_access(directory):
    path=deep_file(directory)
    held=p.Retained(path,path.stat().st_size)
    original=os.close
    checks={}
    def observed(fd):
        if not checks:
            assert held.state=="closing"
            checks["check"]=refused(held.check)
            checks["hash"]=refused(lambda:p.hash_range(held,bytearray(4096),p.IOCount(),p.IO()))
            checks["read"]=refused(lambda:held.readinto(memoryview(bytearray(1))))
            checks["seek"]=refused(lambda:held.seek(0))
            checks["borrowed_read"]=refused(lambda:p.IO().read(held.fd,memoryview(bytearray(1))))
            checks["borrowed_seek"]=refused(lambda:os.lseek(held.fd,0,os.SEEK_SET))
            checks["lease"]=refused(lambda:p.child_lease(held).__enter__())
            checks["adopt"]=refused(lambda:p.child_lease(held).claim_launch())
            checks["reentrant_close"]=refused(held.close)
        return original(fd)
    with patch.object(p.os,"close",observed): held.close()
    assert p.ownership_snapshot()["healthy_zero"]
    return {"case":"closing-access","checks":checks,"cleanup_kind":"healthy-zero"}


def closing_retained_entry(directory):
    paths,sizes,head,_=t.fixture(directory)
    original=os.close;checks=[]
    with ExitStack() as stack:
        inputs=[stack.enter_context(p.Retained(paths[k],sizes[k])) for k in p.NAMES[:7]]
        body=p.Retained(paths[p.NAMES[7]],p.BODY)
        def observed(fd):
            if not checks:
                assert body.state=="closing"
                out=directory/"closing-must-not-create"
                checks.append(refused(lambda:p.compose_from_retained_fixture(inputs+[body],head,out,directory)))
                assert not out.exists()
            return original(fd)
        with patch.object(p.os,"close",observed):body.close()
    assert checks==["owner-not-open"] and p.ownership_snapshot()["healthy_zero"]
    return {"case":"closing-retained-entry","real_retained_entry_refused_after_close_begins":True,"output_created":False,"cleanup_kind":"healthy-zero"}


def lease_generation(directory):
    path=directory/"file";path.write_bytes(b"x")
    with p.Retained(path,1) as held:
        lease=p.child_lease(held)
        with lease:
            assert len(lease.claim_launch())==1
            assert refused(lease.claim_launch)=="stale-child-adoption"
        assert refused(lease.claim_launch)=="stale-child-adoption"
        assert refused(lease.__enter__)=="child-lease"
    assert refused(lambda:p.child_lease(held).__enter__())=="owner-not-open"
    return {"case":"lease-generation","once_only_handoff":True,"stale_adopt_refused":True,"cleanup_kind":"healthy-zero"}


def primary_and_cleanup(directory, kind):
    calls=[];injected=[]
    original_close=os.close
    def fault_close(fd):
        # Scope the fault to an authored retained close, not subprocess internals.
        if not any(token.number==fd and token.state=="closing" for token in p.TOKENS.values()):
            return original_close(fd)
        index=len(calls);calls.append(fd)
        if index in ((0,2) if kind=="constructor" else (0,2,70)):
            error=OSError("synthetic cleanup fault "+str(index));injected.append(error)
            if index==2: original_close(fd)
            raise error
        return original_close(fd)
    if kind=="constructor":
        path=deep_file(directory)
        primary=ValueError("original synthetic constructor check failure")
        with patch.object(p.Retained,"check",side_effect=primary),patch.object(p.os,"close",fault_close):
            try:p.Retained(path,path.stat().st_size)
            except p.CleanupAggregate as error:caught=error
            else:raise AssertionError("constructor failure suppressed")
        assert caught.primary is primary
        retained_result=False
    else:
        paths,sizes,head,_=t.fixture(directory)
        primary=None
        original_transfer=p.transfer
        class Partial(p.IO):
            def __init__(self):self.n=0
            def write(self,fd,view):
                self.n+=1
                if self.n==2:return os.write(fd,view[:13])
                if self.n==3:raise OSError("original actual partial-write boundary")
                return os.write(fd,view)
        def observe_transfer(*args,**kwargs):
            nonlocal primary
            try:return original_transfer(*args,**kwargs)
            except p.Refusal as error:
                primary=error
                raise
        out=directory/"output"
        contexts=[patch.object(p.os,"close",fault_close)]
        if kind=="composition-failure":
            contexts += [patch.object(p,"IO",Partial),patch.object(p,"transfer",observe_transfer)]
        with ExitStack() as stack:
            for context in contexts:stack.enter_context(context)
            try:p.compose_fixture(paths,sizes,head,out,directory)
            except p.CleanupAggregate as error:caught=error
            else:raise AssertionError("cleanup failure suppressed")
        if kind=="composition-failure":
            assert caught.primary is primary and primary.code=="io-error"
            assert primary.progress["write_acknowledged"]==525
            assert out.stat().st_size==525
            retained_result=False
        else:
            assert caught.primary is None
            assert caught.retained_result["profile_bytes"]==p.PROFILE
            assert caught.retained_result["output_acknowledged_bytes"]==p.PROFILE
            assert caught.retained_result["child"]["terminal_reaped"]
            assert out.stat().st_size==p.PROFILE
            retained_result=True
    faults=[f for item in caught.cleanup_errors if isinstance(item,p.CleanupFailure) for f in item.failures]
    expected=2 if kind=="constructor" else 3
    assert len(faults)==expected and all(any(f.exception is error for f in faults) for error in injected)
    assert len(calls)==len(set(calls)),"each numeric close capability consumed once"
    assert len(p.TOKENS)==len(p.UNCERTAIN_CLOSES)==expected
    assert not p.ownership_snapshot()["healthy_zero"]
    primary_record=None if caught.primary is None else {"type":type(caught.primary).__name__,"text":str(caught.primary),"code":getattr(caught.primary,"code",None),"stage":getattr(caught.primary,"stage",None),"progress":getattr(caught.primary,"progress",None),"raw_exception_traceback":traceback.format_exception(caught.primary)}
    return {"case":kind,"original_failure_primary_identity_preserved":kind!="composition-success","original_primary":primary_record,"successful_composition_result_retained":retained_result,"retained_success_observation":caught.retained_result,"close_calls":len(calls),"cleanup_failures":summary(caught),"uncertain_saved_numbers_retried":False,"cleanup_kind":"synthetic-known-fault; terminal uncertainty retained"}


def all_positions_uncertain(directory, mode):
    path=deep_file(directory)
    held=p.Retained(path,path.stat().st_size)
    original=os.close;calls=[]
    def boundary(fd):
        calls.append(fd)
        if mode=="post":original(fd)
        raise OSError("synthetic all-position "+mode)
    with patch.object(p.os,"close",boundary):
        try:held.close()
        except p.CleanupFailure as error:caught=error
        else:raise AssertionError("fault suppressed")
    assert len(calls)==len(set(calls))==65
    assert len(caught.failures)==len(p.UNCERTAIN_CLOSES)==len(p.TOKENS)==65
    assert len({id(f.exception) for f in caught.failures})==65
    assert refused(lambda:p.Retained(path,path.stat().st_size))=="owner-admission-quarantined-or-full"
    return {"case":"all-positions-uncertain","mode":mode,"owned_positions":65,"attempted_once":65,"uncertainties_accounted":65,"all65_original_exceptions_preserved":True,"cleanup_failures":summary(caught),"new_owner_admission_refused":True,"uncertain_saved_numbers_retried":False,"cleanup_kind":"synthetic-known-fault; terminal uncertainty retained"}


def quarantine_number_reuse(directory):
    path=deep_file(directory)
    held=p.Retained(path,path.stat().st_size)
    target=held.fd.saved_number
    original=os.close
    first=True
    def fault(fd):
        nonlocal first
        original(fd)
        if first:
            first=False
            raise OSError("known post-close signal for reuse witness")
    with patch.object(p.os,"close",fault):
        try:held.close()
        except p.CleanupFailure as error:caught=error
        else:raise AssertionError("fault suppressed")
    fresh=[]
    try:
        # Each probe fd is acquired as a NEW known test owner, never by replaying
        # an uncertain number. Natural allocation reaches the released number.
        for _ in range(65):
            fd=os.open(path,os.O_RDONLY);fresh.append(fd)
            if fd==target:break
        assert fresh[-1]==target
        calls=[]
        def observed(fd):calls.append(fd);return original(fd)
        with patch.object(p.os,"close",observed):
            try:held.close()
            except p.CleanupFailure as repeated:assert repeated.report is caught.report
            else:raise AssertionError("quarantine suppressed")
        assert calls==[]
        assert os.read(fresh[-1],128)==b"unchanged quiescent bytes"
        assert refused(lambda:held.seek(0))=="owner-not-open"
        assert len(p.UNCERTAIN_CLOSES)==1
    finally:
        # These numbers came from our fresh successful opens, not the saved
        # uncertainty record. No old close capability is retried.
        for fd in reversed(fresh):original(fd)
    return {"case":"quarantined-number-reuse","natural_number_reuse_without_dup2":True,"fresh_test_owner_preserved":True,"terminal_old_close_additional_syscalls":0,"new_test_owners_acquired_and_closed":len(fresh),"uncertain_record_retained":True,"uncertain_saved_numbers_retried":False,"cleanup_kind":"synthetic-known-fault; terminal uncertainty retained"}


def bounds(directory):
    path=directory/"file";path.write_bytes(b"x")
    with ExitStack() as stack:
        owners=[stack.enter_context(p.Retained(path,1)) for _ in range(9)]
        assert len(p.OWNERS)==9 and len(p.TOKENS)<=585
        before=p.ownership_snapshot()
        assert refused(lambda:p.Retained(path,1))=="owner-admission-quarantined-or-full"
        assert p.ownership_snapshot()==before
        with p.CleanupFrame() as frame:
            frame.adopt(owners[0])
            assert refused(lambda:frame.adopt(owners[0]))=="cleanup-frame-cap"
    assert p.ownership_snapshot()["healthy_zero"]
    return {"case":"bounds","max_owners_observed":9,"tenth_owner_refused_without_new_tokens":True,"duplicate_cleanup_frame_owner_refused":True,"descriptor_record_bound":585,"cleanup_kind":"healthy-zero"}


def nonterminal_child(directory):
    paths,sizes,head,_=t.fixture(directory)
    class Nonterminal:
        returncode=None
        def __init__(self,*args,**kwargs):self.waits=self.kills=0
        def wait(self,timeout):
            self.waits+=1
            raise p.subprocess.TimeoutExpired("model only; no process",timeout)
        def kill(self):self.kills+=1
        def poll(self):return None
    with patch.object(p.subprocess,"Popen",Nonterminal):
        try:p.compose_fixture(paths,sizes,head,directory/"output",directory)
        except p.CleanupAggregate as error:caught=error
        else:raise AssertionError("nonterminal child suppressed")
    assert isinstance(caught.primary,p.Refusal) and caught.primary.code=="unreaped-child-quarantine"
    assert len(p.QUARANTINES)==1
    process,owners=p.QUARANTINES[0]
    assert (process.waits,process.kills)==(3,2)
    assert len(owners)==2 and all(x.live for x in owners)
    for owner in owners:
        assert refused(owner.close)=="child-live"
        assert refused(lambda:owner.seek(0))=="shared-OFD-live"
    assert len(caught.cleanup_errors)==2
    return {"case":"nonterminal-child-model","no_process_created":True,"waits":3,"kills":2,"leased_owners":2,"primary_preserved":True,"cleanup_refusals_retained":2,"cleanup_kind":"modeled lease quarantine; no healthy-zero claim"}


def main(argv):
    if len(argv)<2:raise ValueError("closed argv")
    root=ROOT/"owned-scratch";root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="case-",dir=root) as temp:
        directory=Path(temp)
        if argv[1]=="close-position" and len(argv)==4 and argv[2] in ("pre","post"):
            position=int(argv[3]);assert 0<=position<65
            result=close_position(directory,argv[2],position)
        elif argv[1]=="all-positions-uncertain" and len(argv)==3 and argv[2] in ("pre","post"):
            result=all_positions_uncertain(directory,argv[2])
        elif argv[1]=="stale-reuse" and len(argv)==2:result=stale_reuse(directory)
        elif argv[1]=="closing-access" and len(argv)==2:result=closing_access(directory)
        elif argv[1]=="closing-retained-entry" and len(argv)==2:result=closing_retained_entry(directory)
        elif argv[1]=="lease-generation" and len(argv)==2:result=lease_generation(directory)
        elif argv[1] in ("constructor","composition-failure","composition-success") and len(argv)==2:result=primary_and_cleanup(directory,argv[1])
        elif argv[1]=="nonterminal-child-model" and len(argv)==2:result=nonterminal_child(directory)
        elif argv[1]=="quarantined-number-reuse" and len(argv)==2:result=quarantine_number_reuse(directory)
        elif argv[1]=="bounds" and len(argv)==2:result=bounds(directory)
        else:raise ValueError("closed argv")
        result["ownership_before_test_directory_cleanup"]=p.ownership_snapshot()
    result["ownership_at_child_terminal_exit"]=p.ownership_snapshot()
    result["uncertain_os_close_resolution_qualified"]=False
    result["process_exit_not_a_refund_or_healthy_cleanup_receipt"]=True
    result["authority"]=dict(real_binding=False,runtime=False,ota=False,ga=False)
    sys.stdout.write(json.dumps(result,sort_keys=True,separators=(",",":"))+"\n")


if __name__=="__main__":main(sys.argv)
