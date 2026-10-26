#!/usr/bin/env python3
"""Actual v3 checker witness using synthetic selected policy; never product evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'preaccess'/'retained-synthetic-control-fixture'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def identity(p):
    data=p.read_bytes()
    return {'bytes':len(data),'sha256':sha(data)}

def run(argv,cwd):
    child=subprocess.run([str(x) for x in argv],cwd=cwd,capture_output=True,text=True,
                         timeout=60,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if child.returncode:
        raise AssertionError({'exit':child.returncode,'stdout':child.stdout,'stderr':child.stderr})
    return {'argv':[str(x) for x in argv],'exit':child.returncode,
            'stdout':child.stdout,'stderr':child.stderr}

def main():
    p=argparse.ArgumentParser();p.add_argument('--jdk-home',required=True,type=Path)
    a=p.parse_args();scratch=HERE/'scratch';assert not scratch.exists()
    shutil.copytree(BASE,scratch)
    logs=[];records=[]
    try:
        checker=scratch/'check_qualified_matrix.py'
        command=[sys.executable,'-B',checker,'--policy',scratch/'policy.json',
                 '--map',scratch/'context.json','--source-root',scratch/'sources',
                 '--classes',scratch/'classes','--matrix',scratch/'matrix.json']
        original_context=json.loads((scratch/'context.json').read_bytes())['context_id']
        baseline=run(command,scratch);logs.append({'name':'synthetic-selected-policy-positive',**baseline})
        assert json.loads(baseline['stdout'])['context_id']==original_context
        fixture_root=HERE/'retained-fixture';assert not fixture_root.exists()
        fixture_root.mkdir()
        for version in (1,2):
            # This real emitted support class is intentionally outside the product SourceFile set.
            source=scratch/'sources'/'Support.java'
            source.write_text('package example; public final class Support { public static int marker() { return %d; } }\n'%version)
            producer=scratch/'run_qualified_matrix.py'
            producer.write_text('# Synthetic unexecuted runner source marker %d\n'%version)
            compilation=run([a.jdk_home/'bin/javac','--release','17','-Xlint:all','-Werror','-proc:none',
                '-sourcepath',scratch/'empty-sourcepath','-classpath',scratch/'empty-classpath',
                '-d',scratch/'classes',source],scratch)
            logs.append({'name':'compile-support-version-%d'%version,**compilation})
            support=scratch/'classes/example/Support.class'
            matrix=json.loads((scratch/'matrix.json').read_bytes())
            metadata={'producer':identity(producer),'support_source':identity(source),
                      'support_class':identity(support),'claimed_review_status':'reviewed-exact-execution-closure',
                      'claimed_tool_identity':'synthetic-version-%d'%version}
            matrix['execution_scaffolding']=metadata
            (scratch/'matrix.json').write_text(json.dumps(matrix,sort_keys=True,indent=2)+'\n')
            checked=run(command,scratch);logs.append({'name':'changed-support-and-runner-metadata-version-%d'%version,**checked})
            receipt=json.loads(checked['stdout'])
            assert receipt['status']=='passed-exact-host-qualified-matrix'
            assert receipt['context_id']==original_context
            records.append({'version':version,'metadata':metadata,'checker_receipt':receipt})
            version_root=fixture_root/('version-%d'%version)
            shutil.copytree(scratch,version_root)
        assert records[0]['metadata']['support_class']!=records[1]['metadata']['support_class']
        assert records[0]['metadata']['support_source']!=records[1]['metadata']['support_source']
        assert records[0]['metadata']['producer']!=records[1]['metadata']['producer']
        assert records[0]['checker_receipt']['context_id']==records[1]['checker_receipt']['context_id']
        result={'scope':'Actual released checker control flow under explicitly synthetic selected-policy fixture with local pins. Released draft remains root_selected=false and refuses ordinary entry. No product execution/acceptance claim.',
                'finding':'Product context does not bind actual execution scaffolding; unknown execution_scaffolding metadata is ignored.',
                'witness_reproduced':True,'product_context_id':original_context,
                'same_product_context_accepts_different_support_and_runner':True,
                'records':records,'commands':logs,'children_reaped':True,
                'owned_scratch_removed':True,'native_process_or_capture_started':False,
                'product_policy_context_or_behavior_accepted':False}
        (HERE/'witness.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
        print(json.dumps({'witness_reproduced':True,'accepted_changed_scaffolding_versions':2,
                          'product_context_unchanged':True,'product_accepted':False}))
    finally:
        shutil.rmtree(scratch)

if __name__=='__main__':main()
