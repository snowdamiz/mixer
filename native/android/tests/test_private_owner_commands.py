"""Fake process boundaries with real pipes; no OS process probes, signals or launches."""
import copy
import errno
import importlib.util
import json
import os
from pathlib import Path
import signal
import time
from unittest.mock import patch
import private_owner_commands as adapter

class Child:
    def __init__(self, argv, **kwargs):
        spec = SPECS[argv[0]]
        self.spec = spec
        self.pid = 90000000+len(CHILDREN)
        self.returncode = None
        self.reaped = False
        self.started = time.monotonic()
        self.writers = {}
        for name in ('stdout','stderr'):
            read,write = os.pipe()
            setattr(self,name,os.fdopen(read,'rb',buffering=0))
            self.writers[name] = write
        CHILDREN[self.pid] = self
        self.tick()
    def tick(self):
        elapsed = time.monotonic()-self.started
        for name in list(self.writers):
            if elapsed >= self.spec.get(name+'_delay',0):
                data = self.spec.get(name,b'')
                if data:
                    os.write(self.writers[name],data)
                os.close(self.writers.pop(name))
        if elapsed >= self.spec.get('duration',0) and self.returncode is None:
            self.returncode = self.spec.get('code',0)
    def poll(self):
        EVENTS.append(('reap',self.pid))
        self.tick()
        if self.returncode is not None:
            self.reaped = True
        return self.returncode
    def kill(self):
        self.returncode = -9
        for fd in self.writers.values():
            os.close(fd)
        self.writers.clear()

def group(pid, sig):
    EVENTS.append(('group',pid,sig))
    if pid not in CHILDREN:
        raise AssertionError('unowned synthetic group')
    child = CHILDREN[pid]
    child.tick()
    if child.spec.get('denied'):
        raise PermissionError(errno.EPERM,'fake persistent permission denial')
    if child.returncode is not None:
        if not child.reaped:
            raise PermissionError(errno.EPERM,'fake unreaped zombie')
        raise ProcessLookupError(errno.ESRCH,'fake positively absent group')
    if sig == signal.SIGKILL:
        child.kill()

SPECS = {}
CHILDREN = {}
EVENTS = []

def require(ok, reason):
    if not ok:
        raise AssertionError(reason)

def run_controls(output):
    output = Path(output)
    output.mkdir()
    results = []
    original_pump = adapter.core.Commands.pump
    def pump(manager, seconds=.02):
        for child in CHILDREN.values():
            child.tick()
        return original_pump(manager,seconds)
    def manager(label, spec, output_limit=None, aggregate=None):
        folder = output/label
        folder.mkdir()
        scratch = folder/'scratch'
        scratch.mkdir()
        SPECS[label] = spec
        controlled = adapter.ControlledCommands(folder,{},deadline=time.monotonic()+65)
        if output_limit is not None:
            controlled.commands.output_bytes = output_limit
        if aggregate is not None:
            controlled.commands.total_output_bytes = aggregate
        return controlled,scratch
    def failure(action):
        try:
            action()
        except (RuntimeError,ValueError,OSError):
            return
        raise AssertionError('expected refusal')
    with patch.object(adapter.core.subprocess,'Popen',side_effect=Child), patch.object(adapter.core.os,'killpg',side_effect=group), patch.object(adapter.core.Commands,'pump',pump), patch.object(adapter.core.subprocess,'run',side_effect=AssertionError('unmanaged subprocess forbidden')):
        c,s = manager('three-hundred-seconds',{'stdout':b'ok'})
        require(c.commands.output_bytes==8*1024*1024 and c.commands.total_output_bytes==64*1024*1024 and c.commands.cleanup_seconds==60,'production limits drift')
        c.run('three-hundred-seconds',['three-hundred-seconds'],s,300)
        r = c.commands.records[0]
        require(r['requested_timeout_seconds']==300 and all(r[k] for k in adapter.FACTS),'300-second adapter used capped run() or missing custody')
        require(EVENTS.index(('reap',r['pid'])) < EVENTS.index(('group',r['pid'],signal.SIGKILL)),'zombie ordering regressed')
        require(c.finish(s)['scratchRemoved'],'terminal scratch not cleaned')
        results.append('300-second start/pump/reaped/stop path; exact limits; reap before signal; positive absence; cleanup')
        for name in ('stdout','stderr'):
            label = 'independent-'+name+'-EOF'
            c,s = manager(label,{name:b'delayed',name+'_delay':.05})
            c.run(label,[label],s,.4)
            r = c.commands.records[0]
            require(r['stdout_eof'] and r['stderr_eof'] and r['direct_child_reaped'],'EOF inferred from direct reap')
            require(c.finish(s)['scratchRemoved'],'EOF cleanup')
            results.append(label)
        c,s = manager('time-without-output',{'duration':2})
        failure(lambda:c.run('time-without-output',['time-without-output'],s,.03))
        require(c.commands.records[0]['stop']=='timeout' and c.commands.used_output==0,'time bound depends on output')
        require(c.finish(s)['allTerminalCustody'],'timeout cleanup incomplete')
        results.append('independent wall deadline without output')
        c,s = manager('combined-output',{'stdout':b'a'*700,'stderr':b'b'*700},1024)
        failure(lambda:c.run('combined-output',['combined-output'],s,.5))
        require(c.commands.limit and c.commands.used_output==1024,'combined output cap weakened')
        require(c.finish(s)['allTerminalCustody'],'output cleanup incomplete')
        results.append('combined stdout/stderr output cap independent of time')
        c,s = manager('aggregate-one',{'stdout':b'a'*800},1024,1500)
        c.run('aggregate-one',['aggregate-one'],s,.5)
        SPECS['aggregate-two']={'stderr':b'b'*800}
        failure(lambda:c.run('aggregate-two',['aggregate-two'],s,.5))
        require(c.commands.used_output==1500 and c.commands.limit,'aggregate cap reset between commands')
        failure(lambda:c.run('aggregate-three',['aggregate-one'],s,.5))
        require(len(c.commands.records)==2,'output hold admitted another child')
        require(c.finish(s)['allTerminalCustody'],'aggregate custody incomplete')
        results.append('aggregate output cap persists across commands and closes admission')
        c,s = manager('nonzero',{'stdout':b'failed receipt','code':7})
        failure(lambda:c.run('nonzero',['nonzero'],s,.5))
        require(all(c.commands.records[0][k] for k in adapter.FACTS),'nonzero custody not collected')
        require(c.finish(s)['scratchRemoved'],'nonzero terminal scratch')
        results.append('failed command retains full logs and terminal custody')
        c,s = manager('bounds',{})
        for seconds in (0,-1,300.01):
            failure(lambda:c.run('bounds',['bounds'],s,seconds))
        require(not c.commands.records,'invalid deadline launched child')
        c.finish(s)
        results.append('invalid command deadlines refused before launch')
        c,s = manager('sticky-UNKNOWN',{'denied':True})
        failure(lambda:c.run('sticky-UNKNOWN',['sticky-UNKNOWN'],s,.5))
        require(c.commands.hold and c.commands.records[0]['state']=='UNKNOWN','persistent denial not UNKNOWN')
        at = len(EVENTS)
        failure(lambda:c.run('forbidden-retry',['sticky-UNKNOWN'],s,.5))
        for method in (lambda:c.commands.stop(c.commands.owned[0]),lambda:c.commands.pump(0),lambda:c.commands.reaped(c.commands.owned[0]),lambda:c.finish(s)):
            method()
        require(len(EVENTS)==at and s.exists(),'UNKNOWN performed process operations or removed scratch')
        results.append('sticky UNKNOWN makes all later process operations no-ops and retains scratch')
        c,s = manager('launch-UNKNOWN',{})
        with patch.object(adapter.core.subprocess,'Popen',side_effect=OSError('fake launch failure')):
            failure(lambda:c.run('launch-UNKNOWN',['launch-UNKNOWN'],s,.5))
        require(c.commands.hold and not c.commands.records[0]['direct_child_reaped'],'launch failure inferred absence')
        at = len(EVENTS)
        c.finish(s)
        require(s.exists() and len(EVENTS)==at,'launch UNKNOWN cleanup/probe')
        results.append('launch UNKNOWN preserves scratch without inferred absence')
    for child in CHILDREN.values():
        for fd in child.writers.values():
            os.close(fd)
        child.writers.clear()
        child.stdout.close();child.stderr.close()
    # Exercise the actual preflight against synthetic javap data, and source-map tampering.
    runner_path = Path(__file__).with_name('run-private-owner-host.py')
    spec = importlib.util.spec_from_file_location('private_owner_runner_controls',runner_path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    sample = 'final class dev.mixer.android.A {\n  void call();\n    descriptor: ()V\n    Code:\n       0: invokevirtual #3 // Method x:()V\n    LineNumberTable:\n      line 4: 0\n}\n'
    parsed = runner.parse_javap(sample)
    require(parsed[('dev.mixer.android.A','call','()V')]['instructions'][0][0]=='invokevirtual','javap descriptor parser')
    mapping = json.loads((runner.ROOT/runner.MAPPING).read_text())
    frozen = {s:(runner.ROOT/s).read_bytes() for s in mapping['source_sha256']}
    runner.source_anchors(frozen,mapping)
    altered = copy.deepcopy(mapping)
    altered['records'][0]['candidates'][0]['column'] += 1
    failure(lambda:runner.source_anchors(frozen,altered))
    altered = copy.deepcopy(mapping)
    altered['records'][0]['required_cases'] = ['clean']
    failure(lambda:runner.source_anchors(frozen,altered))
    frozen[mapping['records'][0]['source']] += b' '
    failure(lambda:runner.source_anchors(frozen,mapping))
    results += ['javap parser binds class/method/descriptor/BCI/line','accepted 189 source anchors; mutated column, cases and source bytes refused']
    receipt = {'status':'passed','groups':len(results),'results':results,'realProcessLaunches':0,'realOSGroupCalls':0,'syntheticGroupsOnly':True,'custodian_sha256':adapter.CUSTODIAN_SHA256}
    (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
