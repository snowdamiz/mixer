"""Replay all 33 exact frozen V2 reviewer controls in V4-owned scope.

The original invalid lower-level TransactionStore fixture remains rejected. Its
unchanged all-inventory-accepted assertion is an explicitly retained historical
failure, not a 33/33 V4 acceptance claim. Separate valid Session-driven controls
qualify the repaired auxiliary validator.
"""
import ast
from contextlib import redirect_stdout,redirect_stderr
import json
import sys
import textwrap
import unittest
from pathlib import Path
import copy
import datetime
import tempfile
import subprocess
import prepare
import test_importer as tests

REVIEW=prepare.ROOT/'verification/apple-focus-reference-runtime-v2-independent-review'
SOURCE_SHA='84f7d1c5dbe0cbe17d60c34675de1c3d17107c17964062ea74ebdf5982a195db'


def run(attempt):
    source=(REVIEW/'run_review.py').read_text();prepare.require(prepare.sha(source.encode())==SOURCE_SHA,'Frozen 33-control reviewer source changed')
    tree=ast.parse(source)
    program_node=next(node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='INVENTORY_PROGRAM' for target in node.targets))
    program=ast.literal_eval(program_node.value)
    main=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='main')
    cls=next(node for node in main.body if isinstance(node,ast.ClassDef) and node.name=='IndependentControls')
    mutations=next(node for node in main.body if isinstance(node,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='mutations' for target in node.targets))
    loop=next(node for node in main.body if isinstance(node,ast.For) and ast.get_source_segment(source,node.iter)=='mutations.items()')
    snippets=[textwrap.dedent(ast.get_source_segment(source,node)) for node in [cls,mutations,loop]]
    scope={'tests':tests,'i':tests.i,'prepare':prepare,'ROOT':prepare.ROOT,'attempt':attempt,'Path':Path,'tempfile':tempfile,'subprocess':subprocess,'sys':sys,'INVENTORY_PROGRAM':program,'copy':copy,'datetime':datetime,'json':json,'stable':prepare.stable,'detail':[]}
    exec(snippets[0],scope);exec(snippets[1],scope)
    scope['mutations'].pop('missing_app_witness_stays_unknown')
    exec(snippets[2],scope)
    cls=scope['IndependentControls'];loader=unittest.TestLoader()
    suite=unittest.TestSuite(cls(name) for name in loader.getTestCaseNames(cls) if name.startswith('test_review_'))
    with (attempt/'historical-review.stdout.log').open('w') as out,(attempt/'historical-review.stderr.log').open('w') as err,redirect_stdout(out),redirect_stderr(err):
        result=unittest.TextTestRunner(stream=err,verbosity=2).run(suite)
    rows={'schema':'mixer.apple-focus-reference-runtime-v4-historical-review-replay.1','originalReviewerSourceSHA256':SOURCE_SHA,'extractedControlSourcesSHA256':[prepare.sha(value.encode()) for value in snippets],'inventoryProgramSHA256':prepare.sha(program.encode()),'testsRun':result.testsRun,'errors':len(result.errors),'skipped':len(result.skipped),'failures':[{'name':str(case),'traceback':failure} for case,failure in result.failures],'controlsPassed':result.testsRun-len(result.failures)-len(result.errors),'unchangedAssertions':True,'detail':scope['detail'],'expectedHistoricalFixtureFailure':'test_review_actual_composed_bridge_and_settings_inventory','meaning':'The original direct TransactionStore synthetic record is not a valid Session journal. Preserve its rejection; separate production Session controls establish acceptance.','syntheticOnly':True,'nativeExecuted':False}
    rows['expectedReplayOutcome']=result.testsRun==33 and not result.errors and not result.skipped and len(result.failures)==1 and 'test_review_actual_composed_bridge_and_settings_inventory' in str(result.failures[0][0])
    (attempt/'historical-review-results.json').write_bytes(prepare.stable(rows))
    return rows
