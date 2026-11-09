#!/usr/bin/env python3
"""Require actual Git-selected import/read closure and run the exact eight controls."""
from pathlib import Path
import importlib.util
import io
import json
import os
import stat
import sys
import unittest

def need(value, message):
    if not value: raise RuntimeError(message)

def exercise(root, packet, selection_file, baseline=False):
    root=Path(root).resolve(); here=root/packet
    selection=json.loads(Path(selection_file).read_text())
    selected=set(selection['selected'])
    required=set(selection['required'])
    missing=sorted(required-selected)
    bootstrap='verification/plan-continuation-2026-11-07/generated-java-ci-integration/bootstrap.py'
    membership_pass=not missing
    if baseline: need(missing==[bootstrap], 'R1 must omit exactly canonical bootstrap: '+repr(missing))
    else: need(membership_pass, 'Real Git selection misses runtime/test imports: '+repr(missing))
    observed=set(); transient=set(); directory_reads=set(); active_open=[]; descriptors={}
    original_open=os.open
    def tracked_open(value, flags, mode=0o777, *, dir_fd=None):
        p=Path(os.fsdecode(value))
        if not p.is_absolute():
            if dir_fd is None: p=Path.cwd()/p
            else:
                need(dir_fd in descriptors,'Untracked directory descriptor')
                parent,identity=descriptors[dir_fd];s=os.fstat(dir_fd)
                need((s.st_dev,s.st_ino)==identity,'Directory descriptor identity changed')
                p=parent/p
        active_open.append(p)
        try: fd=original_open(value,flags,mode,dir_fd=dir_fd)
        finally: active_open.pop()
        s=os.fstat(fd)
        if stat.S_ISDIR(s.st_mode): descriptors[fd]=(p,(s.st_dev,s.st_ino))
        return fd
    os.open=tracked_open
    def audit(event,args):
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)): return
        p=(active_open[-1] if active_open else Path(os.fsdecode(args[0])).absolute())
        try: rel=p.relative_to(root).as_posix()
        except ValueError: return
        flags=args[2]
        if flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND): return
        if p.is_dir(): directory_reads.add(rel); return
        if p.suffix=='.pyc' and not p.exists(): return  # absent import-cache lookup is not a repository input
        if '/control-scratch/' in '/'+rel or rel.endswith('/control-scratch'): transient.add(rel); return
        observed.add(rel)
    sys.addaudithook(audit)
    os.chdir(here)
    spec=importlib.util.spec_from_file_location('exact_source113_checkout_controls',here/'test_source113.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    (here/'control-scratch').mkdir(exist_ok=True)
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(module.Source113))
    (here/'control-scratch').rmdir()
    raw=stream.getvalue(); print(raw, file=sys.stderr, end='')
    errors=[{'test':str(test),'traceback':trace} for test,trace in result.errors]
    unselected=sorted(observed-selected)
    need(not module.guard.DENIED,'Denied runtime attempts: '+repr(module.guard.DENIED))
    need(result.testsRun==8 and not result.skipped,'Exact eight controls required')
    if baseline:
        need(len(errors)==1 and not result.failures and 'test_metadata_only_literals_and_actual_admission' in errors[0]['test'] and 'FileNotFoundError' in errors[0]['traceback'] and bootstrap in errors[0]['traceback'],'Wrong R1 failure')
        need(unselected==[bootstrap], 'Wrong R1 attempted read closure: '+repr(unselected))
    else:
        need(result.wasSuccessful(),'Fixed checkout eight-suite failed')
        need(not unselected,'Actual read/import outside Git-selected input closure: '+repr(unselected))
        need(bootstrap in observed,'Canonical bootstrap was not actually opened')
    proof={'mode':'optimized' if sys.flags.optimize else 'normal','baseline':baseline,'membership_pass':membership_pass,'missing':missing,'tests_run':result.testsRun,'passed':result.testsRun-len(result.errors)-len(result.failures),'errors':errors,'failures':len(result.failures),'skipped':len(result.skipped),'actual_eight_pass':result.wasSuccessful(),'observed_repository_reads':sorted(observed),'unselected_reads':unselected,'transient_fixture_read_count':len(transient),'directory_reads':sorted(directory_reads),'denied':module.guard.DENIED,'selection_evidence':str(selection_file),'raw_suite_output':raw,'qualification':'actual Git matching and source-only eight-suite; no compiler/native/CI/release/GA'}
    target=here/('sparse-closure-'+proof['mode']+'.json');target.write_text(json.dumps(proof,indent=2)+'\n')
    return proof

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--packet',required=True);p.add_argument('--selection',required=True);p.add_argument('--baseline',action='store_true');args=p.parse_args()
    value=exercise(args.root,args.packet,args.selection,args.baseline)
    print(json.dumps({k:value[k] for k in ('mode','baseline','membership_pass','missing','tests_run','passed','actual_eight_pass','unselected_reads')}))
    sys.exit(1 if args.baseline else 0)
