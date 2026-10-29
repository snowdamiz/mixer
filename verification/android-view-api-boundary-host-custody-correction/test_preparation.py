"""Pure data and mocked custody only; deny runtime surfaces before subjects import."""
import sys
sys.dont_write_bytecode = True
import ast
from contextlib import ExitStack
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import selectors
import signal
import socket
import subprocess
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = ROOT / "verification/android-view-api-boundary-host-admission"


def need(value, message):
    if not value:
        raise RuntimeError(message)


def denied(*args, **kwargs):
    raise RuntimeError("PREPARATION DENIED actual process/session/group/signal/timer/wait/socket/native query")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run():
    local = HERE / "local"
    local.mkdir(exist_ok=True)
    count = 1
    while (local / ("controls-" + str(count))).exists():
        count += 1
    out = local / ("controls-" + str(count))
    out.mkdir()
    checks = []
    report = {"scope": "guarded source/data and synthetic custody only", "passed": False,
              "command": [sys.executable, "-I", "-B", "-S", str(Path(__file__).resolve())],
              "python": sys.version, "real_runtime_or_process_actions": False,
              "checks": checks, "failed_setups_retained": True, "Git_used": False}
    def check(name, value):
        need(value, name)
        checks.append({"name": name, "passed": True})
    def refuses(name, action):
        try:
            action()
        except (RuntimeError, ValueError, OSError):
            check(name, True)
        else:
            check(name, False)
    try:
        with ExitStack() as guards:
            surfaces = []
            # Preserve the class so the subject can subclass it, but deny its
            # constructor, implicit cleanup and every inherited execution path.
            for module, names in (
                (subprocess, ("run", "call", "check_call", "check_output", "getoutput", "getstatusoutput", "_cleanup", "_fork_exec")),
                (subprocess.Popen, ("__init__", "__del__", "_internal_poll", "_wait", "_try_wait", "poll", "wait", "communicate", "_communicate", "send_signal", "terminate", "kill", "_execute_child", "_posix_spawn")),
                (os, ("system", "popen", "fork", "forkpty", "posix_spawn", "posix_spawnp", "execv", "execve", "execl", "execlp", "execvp", "execvpe", "setsid", "setpgid", "getpgid", "getsid", "getpid", "kill", "killpg", "wait", "waitpid", "waitid", "pipe", "pipe2", "dup", "dup2", "set_blocking", "read")),
                (signal, ("signal", "getsignal", "alarm", "setitimer", "pause", "pthread_kill", "sigwait", "sigwaitinfo", "sigtimedwait", "pthread_sigmask")),
                (time, ("sleep", "monotonic", "perf_counter", "time")),
                (threading, ("Thread", "Timer")),
                (socket, ("socket", "socketpair", "create_connection", "getaddrinfo")),
                (resource, ("setrlimit",)), (selectors, ("DefaultSelector",)),
                (ctypes, ("CDLL", "PyDLL")),
            ):
                for name in names:
                    if hasattr(module, name):
                        guards.enter_context(patch.object(module, name, denied))
                        surfaces.append(getattr(module, "__name__", "Popen") + "." + name)
            # Linux waitid enums/interfaces are synthetic on this Mac host.
            for name,value in (("P_PID",1),("WEXITED",4),("WNOHANG",1),("WNOWAIT",16777216),("CLD_EXITED",1),("CLD_KILLED",2),("CLD_DUMPED",3)):
                guards.enter_context(patch.object(os,name,value,create=True))
            guards.enter_context(patch.object(os,"waitid",denied,create=True))
            guards.enter_context(patch.object(signal,"NSIG",65,create=True))
            surfaces.append("os.waitid (including absent-host interface)")
            for alias in ("_del_safe",):
                if hasattr(subprocess, alias) and hasattr(getattr(subprocess, alias), "waitpid"):
                    guards.enter_context(patch.object(getattr(subprocess, alias), "waitpid", denied))
                    surfaces.append("subprocess." + alias + ".waitpid")
            report["denied_before_subject_import"] = surfaces
            collector = load(HERE / "collect.py", "corrected_guarded_collector")
            custody = load(HERE / "custody.py", "corrected_guarded_custody")
            original = load(ORIGINAL / "collect.py", "baseline_guarded_collector")
            check("subjects import inert under process/native denials", True)
            check("isolated no-site no-bytecode bootstrap", sys.flags.isolated == 1 and sys.flags.no_site == 1 and sys.dont_write_bytecode)
            baseline = json.loads((HERE / "baseline.json").read_bytes())
            check("original seal identity preserved", collector.identity(ORIGINAL / "seal.json")["sha256"] == baseline["original_seal_sha256"])
            check("all original seventeen sealed files unchanged", all(collector.identity(ORIGINAL / r["path"]) == {"bytes":r["bytes"],"sha256":r["sha256"]} for r in baseline["original_seal"]["members"]))
            for name in ("input-manifest.json", "tool-profile.json", "jdk-runtime-members.json", "tool-profile-historical-macos.json", "inspector-review.json", "workflow-actions.json"):
                check(name + " byte-identical to baseline", (HERE/name).read_bytes() == (ORIGINAL/name).read_bytes())
            manifest = json.loads((HERE / "input-manifest.json").read_bytes())
            profile = json.loads((HERE / "tool-profile.json").read_bytes())
            runtime = json.loads((HERE / "jdk-runtime-members.json").read_bytes())
            check("official JDK runtime74 exact bytes", len(runtime)==74 and sum(r["bytes"] for r in runtime)==198674633)
            check("runtime compiler/native inputs pinned", {"bin/java","bin/javac","lib/modules","lib/ct.sym","lib/server/libjvm.so","lib/libjli.so","release"} <= {r["path"] for r in runtime})
            check("root source manifest148 preserved", len(manifest["members"])==148)
            observed = collector.verify_frozen_inputs()
            check("producer115 product16 host103 sdk17 closure", observed["host_inputs"]==103 and observed["sdk_inputs"]==17)
            plan=collector.build_plan(ROOT,out/"plan-only",profile,manifest)
            check("six fixed argv and D8 prefix unchanged exactly", plan==original.build_plan(ROOT,out/"plan-only",profile,manifest))
            commands=plan["commands"]
            check("exact seven children three versions four work", plan["command_count"]==7 and plan["version_commands"]==3 and plan["work_commands"]==4)
            check("focused main only", commands[4]["argv"][-2]=="dev.mixer.android.ViewApiBoundaryTests")
            check("host compiler103 SDK compiler17 explicit Java files", sum(a.endswith('.java') for a in commands[3]["argv"])==103 and sum(a.endswith('.java') for a in commands[5]["argv"])==17)
            for entry in commands: custody._validate(entry["argv"],profile["bounds"])
            check("all original explicit argv bounds remain valid", True)
            report["canonical_command_plan_sha256"]=hashlib.sha256(json.dumps(collector.build_plan(ROOT,Path("/selected/output"),profile,manifest),sort_keys=True,separators=(",",":")).encode()).hexdigest()
            refuses("relative executable denied", lambda:custody._validate(["java"],profile["bounds"]))
            refuses("expanded wall limit denied", lambda:custody._validate(["/fake/java"],{**profile["bounds"],"wall_seconds":61}))
            changed=out/"changed"; changed.write_bytes(b"changed")
            refuses("copied byte mismatch denied",lambda:collector.verify_rows(out,[{"path":"changed","bytes":0,"sha256":"0"*64}]))
            refuses("duplicate row denied",lambda:collector.verify_rows(out,[{"path":"changed",**collector.identity(changed)}]*2))
            refuses("escaping row denied",lambda:collector.verify_rows(out,[{"path":"../out","bytes":0,"sha256":"0"*64}]))
            refuses("missing hosted root selection denied",lambda:collector.validate_selection({},{}))
            workflow=(HERE/"workflow.DRAFT.yml").read_text()
            check("corrected collector draft path and no-site bootstrap", "verification/android-view-api-boundary-host-custody-correction/collect.py" in workflow and "/usr/bin/python3 -I -B -S" in workflow and "host-admission/collect.py" not in workflow)
            check("manual-only draft", "workflow_dispatch:" in workflow and "\n  push:" not in workflow and "\n  pull_request:" not in workflow)
            actions=json.loads((HERE/"workflow-actions.json").read_bytes())["actions"]
            check("pinned action identities unchanged", all(value in workflow for value in actions.values()))
            golden={key:True for key in ("spawned","direct_exit_observed_without_reap","signals_retired","direct_reaped","exact_kernel_waitpid","group_absent","stdout_eof","stderr_eof","preflight_ok","postflight_ok","wait_owner_preconditions")}
            golden.update(exit_code=0,errors=[],held=False,custody_lost=False)
            check("pure terminal reducer positive",custody.terminal_verdict(golden))
            for key in tuple(k for k,v in golden.items() if v is True):
                check("independent terminal requirement "+key,not custody.terminal_verdict({**golden,key:False}))
            for key,value in (("exit_code",1),("errors",["bad"]),("held",True),("custody_lost",True)):
                check("terminal reducer rejects "+key,not custody.terminal_verdict({**golden,key:value}))
            # Exercise actual readonly-precondition logic through a fake libc.
            class Query:
                def __call__(self, signum, replacement, previous):
                    need(signum==signal.SIGCHLD and replacement is None,"query never changes disposition")
                    previous._obj.handler = owner_mode["handler"]
                    previous._obj.flags = owner_mode["flags"]
                    return owner_mode["result"]
            owner_mode={"handler":None,"flags":0,"result":0}
            with ExitStack() as fakes:
                fakes.enter_context(patch.object(sys,"platform","linux"))
                fakes.enter_context(patch.object(platform,"machine",lambda:"x86_64"))
                fakes.enter_context(patch.object(ctypes,"CDLL",lambda *a,**k:SimpleNamespace(sigaction=Query())))
                fakes.enter_context(patch.object(signal,"getsignal",lambda s:signal.SIG_DFL))
                fakes.enter_context(patch.object(subprocess,"_active",[]))
                fakes.enter_context(patch.object(threading,"enumerate",lambda:[threading.main_thread()]))
                check("mock default SIGCHLD without no-wait accepted readonly",custody.wait_owner_preconditions()["read_only_sigaction"])
                for key,value in (("handler",1),("handler",123),("flags",2),("result",-1)):
                    owner_mode.update(handler=None,flags=0,result=0); owner_mode[key]=value
                    refuses("unknown native ownership denied "+key+str(value),custody.wait_owner_preconditions)
                owner_mode.update(handler=None,flags=0,result=0)
                with patch.object(signal,"getsignal",lambda s:signal.SIG_IGN): refuses("Python SIGCHLD ignore denied",custody.wait_owner_preconditions)
                with patch.object(subprocess,"_active",[object()]): refuses("pending Popen reaper denied",custody.wait_owner_preconditions)
                with patch.object(threading,"enumerate",lambda:[threading.main_thread(),object()]): refuses("competing thread denied",custody.wait_owner_preconditions)
                with patch.object(ctypes,"CDLL",denied): refuses("unknown native flags denied",custody.wait_owner_preconditions)
                real_sizeof=ctypes.sizeof
                with patch.object(ctypes,"sizeof",lambda value:8 if value is ctypes.c_int else real_sizeof(value)):
                    refuses("wrong native int geometry denied before query",custody.wait_owner_preconditions)
            modes=("normal","signal-normal","core-normal","stdout-no-eof","group-present","group-eperm","preflight-fail","bad-bounds","owner-unknown","construction-fail","cached-return","waitid-echild","waitid-wrong-pid","waitid-wrong-status","waitid-invalid-signal","waitid-lost-before-signal","waitpid-echild","waitpid-wrong-pid","waitpid-running","waitpid-stopped","waitpid-continued","waitpid-wrong-status","waitpid-list","stream-open-fail","stream-write-fail","initial-write-fail","spawn-write-fail","retirement-write-fail","result-write-fail")
            report["mock_events"]={}
            for mode in modes:
                events=[]; custody.SESSION=custody.CustodySession()
                descriptors={101:[b"synthetic output\n",b""],102:[b""]}
                class Stream:
                    def __init__(self,fd):self.fd=fd
                    def fileno(self):return self.fd
                    def close(self):events.append(("close",self.fd))
                def fake_init(self,*args,**kwargs):
                    need(kwargs["start_new_session"] and kwargs["close_fds"] and kwargs["shell"] is False,"exact mock spawn options")
                    events.append(("spawn",))
                    self.pid=991003; self.returncode=0 if mode=="cached-return" else None; self._child_created=True
                    self.stdout=Stream(101); self.stderr=Stream(102)
                    if mode=="construction-fail":raise OSError("mock exec setup failure")
                class Selector:
                    def __init__(self):self.entries={}
                    def register(self,stream,event,data):self.entries[stream.fd]=(stream,data)
                    def unregister(self,stream):del self.entries[stream.fd]
                    def select(self,timeout):return [(SimpleNamespace(data=data),1) for stream,data in list(self.entries.values())]
                    def close(self):events.append(("selector-close",))
                tick=[0.0]; observed_count=[0]
                def now():
                    tick[0]+=10 if mode in ("stdout-no-eof","waitid-lost-before-signal") else .01
                    return tick[0]
                def waitid(*args):
                    need(args==(os.P_PID,991003,os.WEXITED|os.WNOHANG|os.WNOWAIT),"exact WNOWAIT flags")
                    events.append(("waitid",)); observed_count[0]+=1
                    if mode=="waitid-echild" or (mode=="waitid-lost-before-signal" and observed_count[0]>=7):raise ChildProcessError("mock ECHILD")
                    code=os.CLD_KILLED if mode in ("signal-normal","waitid-invalid-signal") else os.CLD_DUMPED if mode=="core-normal" else os.CLD_EXITED
                    return SimpleNamespace(si_pid=991004 if mode=="waitid-wrong-pid" else 991003,si_code=code,si_status=65 if mode=="waitid-invalid-signal" else 999 if mode=="waitid-wrong-status" else 9 if mode in ("signal-normal","core-normal") else 0)
                def waitpid(*args):
                    need(args==(991003,os.WNOHANG),"raw exact waitpid flags")
                    events.append(("waitpid",))
                    if mode=="waitpid-list":return [991003,0]
                    if mode=="waitpid-echild":raise ChildProcessError("mock ECHILD; Popen would synthesize zero")
                    return (991004 if mode=="waitpid-wrong-pid" else 0 if mode=="waitpid-running" else 991003, 127 if mode=="waitpid-stopped" else 65535 if mode=="waitpid-continued" else 256 if mode=="waitpid-wrong-status" else 9 if mode=="signal-normal" else 137 if mode=="core-normal" else 0)
                def read(fd,limit):
                    need(limit==65536,"finite stream read")
                    if mode in ("stdout-no-eof","waitid-lost-before-signal") and fd==101:return b"without EOF\n"
                    chunk=descriptors[fd].pop(0)
                    if not chunk:events.append(("EOF",fd))
                    return chunk
                def killpg(pgid,sig):
                    need(pgid==991003,"only fake invocation owned group")
                    events.append(("group",sig))
                    if sig==0:
                        if mode=="group-present":return
                        if mode=="group-eperm":raise PermissionError("mock EPERM")
                        raise ProcessLookupError("mock absence")
                real_save=custody.save
                def persist(path,value):
                    events.append(("save",Path(path).name))
                    fail={"initial-write-fail":"command.json","spawn-write-fail":"spawn.json","retirement-write-fail":"signal-authority-retired.json","result-write-fail":"result.json"}.get(mode)
                    if Path(path).name==fail:raise OSError("mock ENOSPC")
                    real_save(path,value)
                real_open=custody.evidence_open
                real_write=custody.evidence_write
                def stream_open(state,path):
                    if mode=="stream-open-fail":
                        try:raise OSError("mock stream open ENOSPC")
                        except OSError as error:
                            custody._lose(state,error)
                            raise
                    return real_open(state,path)
                def stream_write(state,stream,data):
                    if mode=="stream-write-fail":
                        class Broken:
                            def write(self,data):raise OSError("mock stream write ENOSPC")
                        return real_write(state,Broken(),data)
                    return real_write(state,stream,data)
                def flight():
                    if mode=="preflight-fail":raise RuntimeError("mock preflight failed")
                    return {"synthetic":True}
                def owner():
                    if mode=="owner-unknown":raise RuntimeError("mock unknown ownership")
                    return {"synthetic":True}
                with ExitStack() as fakes:
                    for module,name,value in ((custody.NonReapingPopen,"__init__",fake_init),(custody,"wait_owner_preconditions",owner),(os,"waitid",waitid),(os,"waitpid",waitpid),(os,"killpg",killpg),(os,"set_blocking",lambda *a:None),(os,"read",read),(selectors,"DefaultSelector",Selector),(time,"monotonic",now),(time,"sleep",lambda seconds:events.append(("mock-sleep",seconds))),(custody,"save",persist),(custody,"evidence_open",stream_open),(custody,"evidence_write",stream_write)):
                        fakes.enter_context(patch.object(module,name,value))
                    bounds={**profile["bounds"]}
                    if mode=="bad-bounds":bounds["wall_seconds"]=61
                    destination=out/mode
                    if mode=="normal":
                        state=custody.run_command(mode,["/synthetic/java","-version"],out,{},destination,bounds,flight,flight)
                        check("mock normal accepts exact direct proof and two EOFs",state["accepted"])
                    else:
                        refuses("mock "+mode+" refuses",lambda:custody.run_command(mode,["/synthetic/java","-version"],out,{},destination,bounds,flight,flight))
                        state=custody.SESSION.active
                        check(mode+" refusal latched in memory",custody.SESSION.held and state["held"] and not state["accepted"])
                    raw_waits=[j for j,e in enumerate(events) if e[0]=="waitpid"]
                    probes=[j for j,e in enumerate(events) if e==("group",0)]
                    check(mode+" no Popen success status used",not any(e[0]=="Popen-wait" for e in events))
                    if mode in ("normal","signal-normal","core-normal"):
                        check(mode+" EOF precedes retirement and exact wait",max(j for j,e in enumerate(events) if e[0]=="EOF")<next(j for j,e in enumerate(events) if e==("save","signal-authority-retired.json"))<raw_waits[0])
                    if mode=="normal":check("normal one post-reap absence-only probe",len(probes)==1 and probes[0]>raw_waits[0])
                    else:
                        checkpoint=len(events)
                        refuses(mode+" later child denied even after write failure",lambda:custody.run_command("later",["/synthetic/java"],out,{},out/(mode+"-later"),profile["bounds"],flight,flight))
                        check(mode+" no later numeric access or spawn",len(events)==checkpoint)
                    if mode.startswith("waitid-") or mode in ("construction-fail","cached-return","spawn-write-fail","initial-write-fail","retirement-write-fail","stream-open-fail","stream-write-fail"):
                        check(mode+" no false direct reap or terminal probe",not state["direct_reaped"] and not probes)
                    if mode.startswith("waitpid-"):
                        check(mode+" raw failure cannot claim direct reap/probe",len(raw_waits)==1 and not state["direct_reaped"] and not probes and state["signals_retired"])
                    if mode in ("waitid-echild","waitid-wrong-pid","waitid-wrong-status","waitid-invalid-signal","construction-fail","cached-return","spawn-write-fail","retirement-write-fail","stream-open-fail","stream-write-fail"):
                        check(mode+" lost authority prevents all numerical signals",not any(e[0]=="group" for e in events))
                    if mode in ("group-present","group-eperm"):
                        check(mode+" one consumed probe then no access",len(probes)==1 and not any(e[0] in ("group","waitpid","waitid","spawn") for e in events[probes[0]+1:]))
                    if mode=="stdout-no-eof":check("missing EOF independent held evidence",not state["stdout_eof"] and state["stderr_eof"] and state["direct_reaped"] and not probes)
                    if mode=="waitid-lost-before-signal":check("fresh ownership loss before cleanup prevents signal",not any(e[0]=="group" for e in events) and state["custody_lost"])
                    if mode in ("signal-normal","core-normal"):check(mode+" raw signal status proven yet nonzero refused",state["direct_reaped"] and state["exit_code"]==-9)
                report["mock_events"][mode]=events
            custody.SESSION=custody.CustodySession()
            unknown={"ownership_valid":True,"custody_lost":False,"signals_retired":False,"direct_reaped":False,"spawned":True,"pid":991003,"pgid":991003}
            refuses("unregistered state cannot observe numeric direct identity",lambda:custody.observe_direct(unknown))
            refuses("unregistered state cannot signal numeric group",lambda:custody.signal_owned(unknown,signal.SIGKILL,"denied"))
            check("unregistered authority refusal latches memory before writes",custody.SESSION.held and unknown["signals_retired"] and unknown["custody_lost"])
            # Reimports share the held session and cannot create a child/output.
            shared=custody.CustodySession(); shared.held=True
            with patch.object(sys,"_mixer_view_api_custody_session",shared):
                fresh=load(HERE/"custody.py","reimported_guarded_custody")
                check("custody hold survives fresh subject module import",fresh.SESSION is shared)
                refuses("fresh imported custody cannot use new record directory",lambda:fresh.run_command("fresh",["/synthetic/java"],out,{},out/"fresh-module",profile["bounds"],lambda:{},lambda:{}))
                check("held reimport does not create record directory",not(out/"fresh-module").exists())
            # Inert destructor and forbidden inherited reapers never call OS.
            custody.SESSION=custody.CustodySession()
            child=custody.NonReapingPopen.__new__(custody.NonReapingPopen)
            child.__del__(); check("inert destructor has no implicit reaper",True)
            for name in ("poll","wait","_internal_poll","_wait","_try_wait","_handle_exitstatus","communicate","_communicate","send_signal","terminate","kill","__enter__","__exit__"):
                refuses("inherited implicit/public path denied "+name,lambda name=name:getattr(child,name)())
            nonce="a"*64; selection={"dispatch_nonce":nonce,"github_sha":"b"*40}; env={"RUNNER_TEMP":str(out),"GITHUB_RUN_ID":"123"}
            reservation=collector.reserve_session(selection,out/"reservation-output",env)
            check("durable one-shot reservation created as data",Path(reservation["path"]).is_file())
            refuses("fresh output cannot bypass same nonce reservation",lambda:collector.reserve_session(selection,out/"different-output",env))
            partial=out/(".mixer-view-api-custody-"+"c"*64+".reservation.json");partial.write_bytes(b"")
            refuses("partial failed reservation blocks retry",lambda:collector.reserve_session({**selection,"dispatch_nonce":"c"*64},out/"third-output",env))
            with patch.object(sys,"_mixer_view_api_collect_invoked",True,create=True):
                fresh=load(HERE/"collect.py","reimported_guarded_collector")
                refuses("collector entry hold survives fresh module",lambda:fresh.collect(out/"none",out/"never-created"))
                check("held collector entry precedes output creation",not(out/"never-created").exists())
            with patch.object(sys,"_mixer_view_api_collect_invoked",False,create=True):
                refuses("failed entry filesystem setup refuses",lambda:collector.collect(out/"none","relative"))
                check("entry reservation survives early setup failure",sys._mixer_view_api_collect_invoked is True)
            for name in ("collect.py","custody.py","test_preparation.py"):
                check(name+" parses as source data",isinstance(ast.parse((HERE/name).read_text()),ast.Module))
            report["source_identities"]={name:collector.identity(HERE/name) for name in ("collect.py","custody.py","test_preparation.py","input-manifest.json","tool-profile.json","workflow.DRAFT.yml")}
            report["preparation_interpreter"]={"path":str(Path(sys.executable).resolve()),**collector.identity(sys.executable)}
            report["frozen_source_observation"]=observed
            report["passed"]=True
    except BaseException as error:
        report["error"]=type(error).__name__+": "+str(error)
        raise
    finally:
        (out/"result.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"passed":report["passed"],"checks":len(checks),"evidence":str(out/"result.json")}))


if __name__=="__main__":
    run()
