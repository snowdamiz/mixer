"""Replay every frozen V4 independent control with only namespace/path adaptation."""
import ast
import copy
from contextlib import redirect_stdout,redirect_stderr
import datetime
import difflib
import inspect
from decimal import (Decimal,Context,localcontext,ROUND_CEILING,ROUND_DOWN,ROUND_FLOOR,
                     ROUND_HALF_DOWN,ROUND_HALF_EVEN,ROUND_HALF_UP,ROUND_UP,ROUND_05UP,
                     InvalidOperation,Inexact)
from fractions import Fraction
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
import textwrap
import time
import types
import unittest
from unittest import mock
import prepare
import test_importer as frozen
from derive_v5 import namespace

def run(attempt):
    source=prepare.ROOT/'verification/apple-focus-reference-runtime-v4-independent-review/run_independent.py'
    raw=source.read_text()
    meta=json.loads((prepare.BASE/'input-bindings.json').read_bytes())
    original_hash=meta['bindings'][str(source.relative_to(prepare.ROOT))]['sha256']
    assert prepare.sha(raw.encode())==original_hash
    tree=ast.parse(raw)
    node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='IndependentControls')
    original=ast.get_source_segment(raw,node);adapted=namespace(original)
    records=[];property_counts={};context_records=[]
    out=attempt/'v4-independent-controls';out.mkdir()
    supplement=prepare.ROOT/'verification/apple-focus-reference-runtime-v4-independent-review/supplemental-inputs.json'
    shutil.copyfile(supplement,prepare.BASE/'supplemental-inputs.json')
    scope=dict(globals(),OWNED=prepare.BASE,base=prepare.BASE,OUT=out,meta=meta,records=records,
               property_counts=property_counts,context_records=context_records,i=frozen.i,
               sha=prepare.sha,stable=prepare.stable)
    exec(compile(adapted,str(source)+' namespace-only V5','exec'),scope)
    cls=scope['IndependentControls']
    # Schema 5 rejects unsupported roots in configure_root, before this frozen
    # review helper's capture try block. Root explicitly approved this helper-only
    # routing: preserve the actual raised error and unchanged timestamp data, then
    # raise that same object at the existing assertion boundary. No successful
    # root selection, capture or summary is fabricated for an invalid root.
    original_helper=textwrap.dedent(inspect.getsource(frozen.RuntimeControls.adapter_namespace))
    old="    namespace['configure_root'](f['root'])\n"
    new="""    deferred_root_error=None
    try:namespace['configure_root'](f['root'])
    except ValueError as error:
        if str(error)!='Canonical exactly representable root ISO timestamp required':raise
        deferred_root_error=error
"""
    assert original_helper.count(old)==1
    helper=original_helper.replace(old,new)
    old='    return namespace,invoke,calls,types.SimpleNamespace(RUN_DIR=output/\'runtime\')\n'
    new="""    if deferred_root_error is not None:
        deferred_root_errors.append({'root':copy.deepcopy(f['root']),'type':type(deferred_root_error).__name__,'message':str(deferred_root_error),'stage':'actual configure_root rejected before capture'})
        def rejected_capture(*args,**kwargs):raise deferred_root_error
        namespace['capture_official']=rejected_capture
    return namespace,invoke,calls,types.SimpleNamespace(RUN_DIR=output/'runtime')
"""
    assert helper.count(old)==1;helper=helper.replace(old,new)
    deferred_root_errors=[];helper_scope=dict(vars(frozen),deferred_root_errors=deferred_root_errors)
    exec(compile(helper,'V5 replay-only early-root routing helper','exec'),helper_scope)
    with mock.patch.object(frozen.RuntimeControls,'adapter_namespace',helper_scope['adapter_namespace']),\
         (out/'stdout.log').open('w') as stdout,(out/'stderr.log').open('w') as stderr,redirect_stdout(stdout),redirect_stderr(stderr):
        result=unittest.TextTestRunner(stream=stderr,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
    rows={'schema':'mixer.apple-focus-reference-runtime-v5-v4-independent-replay.1',
          'originalSourceSHA256':original_hash,'originalControlClassSHA256':prepare.sha(original.encode()),
          'adaptedControlClassSHA256':prepare.sha(adapted.encode()),'onlyExplicitNamespacePathAdaptation':True,
          'controlBodiesAndAssertionsUnchangedApartFromNamespacePaths':True,
          'rootApprovedReplayOnlyHelperAdaptation':'Route only actual configure_root ValueError to the existing capture rejection assertion boundary; timestamp data unchanged',
          'originalHelperSHA256':prepare.sha(original_helper.encode()),'adaptedHelperSHA256':prepare.sha(helper.encode()),
          'actuallyObservedEarlyRootRejections':deferred_root_errors,
          'controlNames':unittest.defaultTestLoader.getTestCaseNames(cls),
          'testsRun':result.testsRun,'controlsPassed':result.testsRun-len(result.failures)-len(result.errors),
          'failures':[{'name':str(c),'traceback':tb} for c,tb in result.failures],
          'errors':[{'name':str(c),'traceback':tb} for c,tb in result.errors],'skipped':result.skipped,
          'actualAdapterAttempts':len(records),'actualDerivedSummaryCalls':sum(r['actualDerivedRuntimeSummaryCalled'] for r in records),
          'hostileContextProfiles':len(context_records),'properties':property_counts,
          'passed':result.wasSuccessful() and result.testsRun==36,'syntheticOnly':True,'nativeExecuted':False}
    (out/'original-control-class.py').write_text(original)
    (out/'namespace-control-class.py').write_text(adapted)
    (out/'original-adapter-helper.py').write_text(original_helper)
    (out/'early-root-replay-helper.py').write_text(helper)
    (out/'early-root-helper.patch').write_text(''.join(difflib.unified_diff(original_helper.splitlines(True),helper.splitlines(True),fromfile='frozen-adapter-helper.py',tofile='replay-only-early-root-helper.py')))
    (out/'adapter-results.json').write_bytes(prepare.stable(records))
    (out/'context-results.json').write_bytes(prepare.stable(context_records))
    (out/'receipt.json').write_bytes(prepare.stable(rows))
    return rows
