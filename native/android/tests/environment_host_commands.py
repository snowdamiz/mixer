"""Durable admission for the two environment JVM harnesses; installed custodian owns commands."""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from private_owner_commands import ControlledCommands, CUSTODIAN_SHA256, FACTS

PROFILE = 'native/android/app/src/dev/mixer/android/AndroidUIProfile.java'
SUPPORT = tuple('native/android/tests/'+name for name in (
    'environment_host_commands.py', 'private_owner_commands.py', 'private_owner_cleanup_control.py'))
MINIMUM_USEFUL_WORK_SECONDS = 2.0

STRIP = ('_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','JDK_JAVA_OPTIONS','CLASSPATH','JAVA_OPTS','JDK_JAVAC_OPTIONS','TOOLCHAINS')

def check(value, message):
    if not value:
        raise RuntimeError(message)

def ident(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}

def save(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('w') as stream:
        stream.write(json.dumps(value,indent=2,sort_keys=True)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary,path)
    directory = os.open(path.parent,os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)

def freeze_sources(root, sources):
    check(len(sources)==len(set(sources)), 'duplicate explicit source')
    check(PROFILE in sources, 'actual AndroidUIProfile required in every closure')
    frozen, names = {}, []
    for source in sources:
        check(not Path(source).is_absolute() and '..' not in Path(source).parts, 'source outside repository')
        data = (root/source).read_bytes()
        package = re.search(rb'\bpackage\s+([\w.]+)\s*;',data)
        check(package is not None, 'explicit package required: '+source)
        names.append(package.group(1).decode()+'.'+Path(source).stem)
        frozen[source] = data
    check(len(names)==len(set(names)), 'duplicate source FQCN')
    return frozen, names

def directory_identity(path):
    stat = path.stat()
    return {'device':stat.st_dev,'inode':stat.st_ino}

class HostCommands:
    def __init__(self, evidence, scratch, env, *, active_seconds):
        check(0 < active_seconds <= 240, 'active budget must be in (0,240] seconds')
        self.evidence, self.scratch = evidence, scratch
        check(evidence.is_dir() and scratch.is_dir() and scratch.resolve()==scratch and scratch.parent==evidence, 'invalid evidence/scratch')
        self.started = time.monotonic()
        self.deadline = self.started+active_seconds+60
        self.control = ControlledCommands(evidence,env,deadline=self.deadline)
        self.identity = None
        self.admissions = []
        self.closed = False
        self.failed = False
        self.unknown_hold = None
        self.unknown_error = None
        self.cleanup_result = None
        self.finishing = False
        self.finalizing = False
        self.finalize_cleanup = False
        self.final_receipt = None

    def prepare(self, frozen, tools, plans):
        self.check_open()
        check(self.identity is None, 'launch identity already sealed')
        for tool in tools.values():
            check(tool.is_file() and os.access(tool,os.X_OK), 'executable tool required before launch: '+str(tool))
        self.identity = {
            'evidence':str(self.evidence), 'scratch':str(self.scratch),
            'evidence_identity':directory_identity(self.evidence), 'scratch_identity':directory_identity(self.scratch),
            'sources':{s:ident(data) for s,data in frozen.items()},
            'tools':{name:{'path':str(tool),**ident(tool.read_bytes())} for name,tool in tools.items()},
            'python':{'path':str(Path(sys.executable).resolve()),'version':sys.version,**ident(Path(sys.executable).read_bytes())},
            'commands':{label:{'argv':list(map(str,argv)),'timeout_seconds':seconds} for label,(argv,seconds) in plans.items()},
            'deadline_monotonic':self.deadline, 'active_deadline_monotonic':self.deadline-60,
            'minimum_useful_work_seconds':MINIMUM_USEFUL_WORK_SECONDS,
            'cleanup_reserve_seconds':60, 'per_command_bytes':8*1024*1024, 'aggregate_bytes':64*1024*1024,
            'custodian_sha256':CUSTODIAN_SHA256,
            'custody_scope':'direct child, separate EOFs and owned group only; outer transport and escaped descendants unproven'}
        save(self.evidence/'launch-identity.json',self.identity)
        save(self.evidence/'admissions.json',self.admissions)

    def latch_unknown(self, operation, error=None):
        # State changes precede every persistence callback. Keep the first cause by identity.
        self.closed = self.failed = True
        commands = self.control.commands
        if self.unknown_hold is None:
            self.unknown_error = error
            unresolved = [r for r in commands.records if not all(r[k] for k in FACTS)]
            self.unknown_hold = commands.hold or {
                'label':unresolved[-1]['label'] if unresolved else None,
                'operation':operation, 'error':repr(error) if error is not None else None,
                'error_type':type(error).__name__ if error is not None else None}
            for record in unresolved:
                record['state'] = 'UNKNOWN'
        commands.hold = self.unknown_hold
        return self.unknown_hold

    def observe_unknown(self):
        if self.unknown_hold is not None or self.control.commands.hold:
            self.latch_unknown('observe-existing-hold')

    def unknown_cleanup(self):
        commands = self.control.commands
        return {'allTerminalCustody':False, 'scratchRemoved':False,
                'hold':self.unknown_hold, 'scratchRetainedForFailure':True,
                'retention_reason':'UNKNOWN; retain frozen scratch and logs',
                'aggregateBytes':commands.used_output, 'aggregateLimit':commands.total_output_bytes}

    def persist_hold(self):
        save(self.evidence/'HOLD.json',{'hold':self.unknown_hold,
            'commands':str(self.evidence/'commands.json'),
            'policy':'sticky UNKNOWN; retain scratch; no further process operations or retry'})

    def check_open(self):
        self.observe_unknown()
        check(self.unknown_hold is None, 'sticky UNKNOWN; admission closed')
        check(not self.closed, 'command admission closed: failed run or finalization')

    def useful_work(self):
        self.check_open()
        self.control.commands.admissible()
        remaining = self.control.commands.deadline-self.control.commands.cleanup_seconds-time.monotonic()
        check(remaining >= MINIMUM_USEFUL_WORK_SECONDS,
              'command admission closed: minimum useful work requires '+str(MINIMUM_USEFUL_WORK_SECONDS)+' active seconds')

    def add_plan(self, label, argv, seconds):
        self.check_open()
        check(self.identity is not None and label not in self.identity['commands'], 'duplicate or unprepared command')
        self.identity['commands'][label] = {'argv':list(map(str,argv)),'timeout_seconds':seconds}
        save(self.evidence/'launch-identity.json',self.identity)

    def run(self, label):
        self.check_open()
        check(self.identity is not None, 'launch identity required')
        try:
            plan = self.identity['commands'][label]
            executable = Path(plan['argv'][0])
            check(executable.is_file() and os.access(executable,os.X_OK), 'executable unavailable before admission')
            check(any(t['path']==str(executable) and ident(executable.read_bytes())['sha256']==t['sha256'] for t in self.identity['tools'].values()), 'tool changed before admission')
            check(directory_identity(self.scratch)==self.identity['scratch_identity'] and directory_identity(self.evidence)==self.identity['evidence_identity'], 'owned directory identity changed')
            self.useful_work()
            self.admissions.append({'label':label, **plan, 'cwd':str(self.scratch),'prepared_monotonic':time.monotonic()})
            save(self.evidence/'admissions.json',self.admissions)
            # Persistence consumes active time; recheck immediately before the installed boundary.
            self.useful_work()
            return self.control.run(label,plan['argv'],self.scratch,plan['timeout_seconds'])
        except BaseException as error:
            self.closed = self.failed = True
            if self.control.commands.hold or any(not all(r[k] for k in FACTS) for r in self.control.commands.records):
                self.latch_unknown('run:'+label,error)
            raise
        finally:
            try:
                records=self.control.commands.records
                if records and records[-1]['label']==label:
                    for stream,source in records[-1].get('logs',{}).items():
                        (self.evidence/(label+'.'+stream)).write_bytes(Path(source).read_bytes())
            except BaseException:
                self.closed = self.failed = True
                raise

    def finish(self, *, failed):
        self.closed = True
        self.observe_unknown()
        if self.cleanup_result is not None:
            return self.cleanup_result
        check(not self.finishing and not (self.finalizing and not self.finalize_cleanup),
              'command finalization already in progress; admission closed')
        self.finishing = True
        try:
            failed = failed or self.failed
            if self.unknown_hold is not None:
                result = self.unknown_cleanup()
            else:
                try:
                    result = self.control.finish(self.scratch,retain_scratch=failed)
                except BaseException as error:
                    self.latch_unknown('finish',error)
                    result = self.unknown_cleanup()
                    result['cleanupError'] = repr(error)
                else:
                    self.observe_unknown()
                    if not result['allTerminalCustody']:
                        self.latch_unknown('finish-incomplete')
                    if self.unknown_hold is not None:
                        result = dict(result,**self.unknown_cleanup())
                    else:
                        result['scratchRetainedForFailure'] = result.pop('scratchRetainedForInterruption',False)
                        result['retention_reason'] = 'failed harness; retain frozen scratch and logs' if failed else None
            # Cache before persistence can re-enter finish. Never stop a closed adapter twice.
            self.cleanup_result = result
            if self.unknown_hold is not None:
                self.persist_hold()
            return result
        finally:
            self.finishing = False

    def finalize(self, root, frozen, receipt, *, success_statuses):
        self.closed = True
        self.observe_unknown()
        check(not self.finalizing and not self.finishing,
              'command finalization already in progress; admission closed')
        if self.final_receipt is not None:
            return self.final_receipt
        self.finalizing = True
        try:
            try:
                receipt['source_stable'] = all((root/s).read_bytes()==data for s,data in frozen.items())
            except BaseException as error:
                receipt['source_stable'] = False
                receipt['source_postflight_error'] = {'type':type(error).__name__,'message':str(error)}
            if not receipt['source_stable']:
                self.failed = True
                if receipt['status']!='UNKNOWN':receipt['status']='failed'
            self.finalize_cleanup = True
            try:
                receipt['cleanup'] = self.finish(failed=receipt['status'] not in success_statuses)
            except BaseException as error:
                self.latch_unknown('finalize-cleanup',error)
                receipt['cleanup'] = self.cleanup_result or self.unknown_cleanup()
                receipt['cleanup_persistence_error'] = {'type':type(error).__name__,'message':str(error)}
            finally:
                self.finalize_cleanup = False
            if self.unknown_hold is not None or not receipt['cleanup']['allTerminalCustody']:
                receipt['status']='UNKNOWN'
            self.final_receipt = receipt
            save(self.evidence/'receipt.json',receipt)
            return receipt
        finally:
            self.finalizing = False
