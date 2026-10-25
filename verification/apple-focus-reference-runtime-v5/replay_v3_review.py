"""Replay exact frozen V3 reviewer methods, mutations and composed programs in V5."""
import ast
import copy
from contextlib import redirect_stdout,redirect_stderr
import datetime
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest
import prepare
import test_importer as tests

REVIEW=prepare.ROOT/'verification/apple-focus-reference-runtime-v3-independent-review'
SOURCE_SHA='eaeab5532ef11e0ffe7d9a73c44b64de6f60c7e180d61ed65b7d5d99dbd9624b'

def run(attempt):
    source=(REVIEW/'run_review.py').read_text()
    prepare.require(prepare.sha(source.encode())==SOURCE_SHA,'Frozen V3 reviewer changed')
    tree=ast.parse(source)
    assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='INDEPENDENT_PROGRAM' for t in n.targets))
    program=ast.literal_eval(assignment.value)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    cls=next(n for n in main.body if isinstance(n,ast.ClassDef) and n.name=='IndependentControls')
    mutations=next(n for n in main.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='mutations' for t in n.targets))
    loop=next(n for n in main.body if isinstance(n,ast.For) and ast.get_source_segment(source,n.iter)=='mutations.items()')
    snippets=[textwrap.dedent(ast.get_source_segment(source,n)) for n in [cls,mutations,loop]]
    details=[]
    scope={'tests':tests,'i':tests.i,'prepare':prepare,'ROOT':prepare.ROOT,'attempt':attempt,'Path':Path,'tempfile':tempfile,'subprocess':subprocess,'sys':sys,'INDEPENDENT_PROGRAM':program,'copy':copy,'datetime':datetime,'json':json,'stable':prepare.stable,'details':details,'Decimal':Decimal}
    for snippet in snippets:exec(snippet,scope)
    cls=scope['IndependentControls'];loader=unittest.TestLoader()
    names=[n for n in loader.getTestCaseNames(cls) if n.startswith('test_independent_')]
    with (attempt/'v3-review.stdout.log').open('w') as out,(attempt/'v3-review.stderr.log').open('w') as err,redirect_stdout(out),redirect_stderr(err):
        result=unittest.TextTestRunner(stream=err,verbosity=2).run(unittest.TestSuite(cls(n) for n in names))
    rows={'schema':'mixer.apple-focus-reference-runtime-v5-v3-review-replay.1','originalReviewerSourceSHA256':SOURCE_SHA,'extractedControlSourcesSHA256':[prepare.sha(s.encode()) for s in snippets],'compositionProgramSHA256':prepare.sha(program.encode()),'controlNames':names,'testsRun':result.testsRun,'controlsPassed':result.testsRun-len(result.failures)-len(result.errors),'failures':[{'name':str(c),'traceback':tb} for c,tb in result.failures],'errors':[{'name':str(c),'traceback':tb} for c,tb in result.errors],'skipped':result.skipped,'unchangedControlBodiesMutationsAssertions':True,'composedInventoryControls':{'run':len(scope['mutations']),'passed':sum(n.startswith('test_independent_composition_') and all(str(c)!=str(cls(n)) for c,_ in result.failures+result.errors) for n in names)},'details':details,'passed':result.wasSuccessful() and result.testsRun==37 and len(scope['mutations'])==25,'syntheticOnly':True,'nativeExecuted':False}
    (attempt/'v3-review-results.json').write_bytes(prepare.stable(rows))
    (attempt/'v3-review-composition-program.py').write_text(program)
    return rows
