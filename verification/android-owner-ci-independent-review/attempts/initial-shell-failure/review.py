#!/usr/bin/env python3
"""Bounded CI glue audit only. Does not execute any product/native host suite."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
LOCAL=ROOT/'verification/android-owner-ci-integration/local'
JOB='android-owner-host'
ROSTER='verification/android-private-owner-effect-roster-amendment/required-host-roster.json'
BARRIER='verification/android-private-owner-integration-implementation/barrier-map.json'
DESCRIPTOR='verification/ui-measured-appearance-v2-contract/mixer-measured-default-v2.json'
OWNER='native/android/tests/run-private-owner-host.py'
OBSERVER='native/android/tests/run-environment-observer-host.py'

def identity(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def load(path):return json.loads(path.read_text())
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
def check(condition,message):
    if not condition:raise RuntimeError(message)

class Review:
    def __init__(self):
        self.commands=[];self.inputs={}
        self.receipt={'schema':1,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'argv':[sys.executable,*sys.argv],'cwd':str(ROOT),'python':sys.version,
          'python_executable':{'path':str(Path(sys.executable).resolve()),**identity(Path(sys.executable).resolve().read_bytes())},
          'script':identity(Path(__file__).read_bytes()),'status':'failed',
          'scope':'new android-owner-host CI glue, dependency metadata, existing raw local receipts and exact source paths only',
          'new_product_behavior_tests':0,'native_UI_capture_or_process_inventory':False,
          'remote_Linux_JDK17_pass_claimed':False,'native_or_GA_acceptance':False}
    def read(self,relative):
        data=(ROOT/relative).read_bytes();self.inputs[relative]=identity(data);return data
    def command(self,label,argv,stdin=None):
        argv=list(map(str,argv));folder=BASE/'commands'/label;folder.mkdir(parents=True)
        actual=Path(argv[0]).resolve();start=time.monotonic()
        record={'argv':argv,'cwd':str(ROOT),'timeout_seconds':20,
                'executable':{'path':str(actual),**identity(actual.read_bytes())},
                'stdin':identity(stdin) if stdin is not None else None}
        result=subprocess.run(argv,cwd=ROOT,input=stdin,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20)
        for name,data in [('stdout',result.stdout),('stderr',result.stderr)]:
            check(len(data)<1_048_576,'audit output cap');(folder/name).write_bytes(data);record[name]=identity(data)
        record.update(exit=result.returncode,elapsed_seconds=time.monotonic()-start)
        save(folder/'receipt.json',record);self.commands.append(record)
        check(result.returncode==0,'audit command '+label)
        return result.stdout
    def workflow(self):
        workflow=self.read('.github/workflows/verify.yml');third=self.read('THIRD_PARTY.yml')
        self.command('ruby-version',['/usr/bin/ruby','--version'])
        self.command('bash-version',['/bin/bash','--version'])
        self.command('git-version',['/usr/bin/git','--version'])
        self.command('python-version',[sys.executable,'--version'])
        head=self.command('head-context',['/usr/bin/git','rev-parse','HEAD']).decode().strip()
        self.receipt['head_context_only']=head
        old=self.command('workflow-HEAD',['/usr/bin/git','show',head+':.github/workflows/verify.yml'])
        text=workflow.decode();start=text.index('  android-owner-host:\n');end=text.index('  swift:\n',start)
        block=text[start:end]
        check((text[:start]+text[end:]).encode()==old,'unrelated workflow changed')
        (BASE/'android-owner-host.yml').write_text(block)
        (BASE/'workflow.yml').write_bytes(workflow)
        ruby='require "json"; require "yaml"; puts JSON.generate(YAML.load(STDIN.read))'
        parsed=json.loads(self.command('parse-workflow',['/usr/bin/ruby','-e',ruby],workflow))
        job=parsed['jobs'][JOB];save(BASE/'parsed-job.json',job)
        check(set(job)=={'runs-on','timeout-minutes','steps'},'unsupported new job key')
        check(job['runs-on']=='ubuntu-24.04' and job['timeout-minutes']==15,'platform/job cap')
        steps=job['steps'];check(len(steps)==5 and steps[0]=={'uses':'actions/checkout@v4'},'job steps')
        expected=[(OWNER,'A','android-owner-orchestration',5),(OWNER,'B','android-owner-renderer',7),
                  (OBSERVER,None,'android-owner-observer',2)]
        for index,(runner,closure,evidence,cap) in enumerate(expected,1):
            step=steps[index];check(set(step)=={'name','timeout-minutes','run'} and step['timeout-minutes']==cap,'step control')
            shell=step['run'];script=BASE/('step-'+str(index)+'.sh');script.write_text(shell)
            self.command('shell-syntax-'+str(index),['/bin/bash','-n',script])
            check(shell.splitlines()[0]==': "${JAVA_HOME_17_X64:?The runner\'s official JDK 17 is required}"','explicit JDK17 precondition')
            check(shell.count('python3 -B '+runner+' \\\n')==1 and '--jdk "$JAVA_HOME_17_X64"' in shell,'exact runner and JDK')
            check('--evidence "$RUNNER_TEMP/'+evidence+'"' in shell,'evidence path')
            check(('--closure '+closure in shell) if closure else '--closure' not in shell,'closure selection')
            check('--skip-matrix' not in shell and 'continue-on-error' not in step,'matrix and failure propagation')
        upload=steps[4]
        check(upload['if']=='always()' and upload['uses']=='actions/upload-artifact@v4','failure evidence upload')
        check(upload['with']=={'name':'android-owner-host-${{ github.sha }}','retention-days':14,
              'if-no-files-found':'warn','path':'${{ runner.temp }}/android-owner-*/'},'artifact path/name/retention')
        check('continue-on-error' not in job,'job failure masked')
        oldthird=self.command('third-party-HEAD',['/usr/bin/git','show',head+':THIRD_PARTY.yml'])
        thirdtext=third.decode();depstart=thirdtext.index('  - name: OpenJDK compiler and Java standard library\n')
        depend=thirdtext.index('  - name: Mint\n',depstart)
        check((thirdtext[:depstart]+thirdtext[depend:]).encode()==oldthird,'unrelated dependency metadata changed')
        parsedthird=json.loads(self.command('parse-third-party',['/usr/bin/ruby','-e',ruby],third))
        dependency=parsedthird['dependencies'][0]
        check(dependency=={'name':'OpenJDK compiler and Java standard library','origin':'https://openjdk.org/',
              'version':'Java-17-host-contract-local-and-CI-version-recorded-per-receipt','license':'GPL-2.0-with-Classpath-Exception',
              'purpose':'independently-authored-Android-owner-observer-and-renderer-host-tests',
              'distribution':'external-verification-toolchain-not-linked-into-product','owner':'android-verification'},'OpenJDK metadata')
        save(BASE/'metadata-review.json',{'dependency':dependency,'workflow_only_new_job':True,'third_party_only_new_entry':True,
          'existing_job_behavior_reviewed':False,'failure_semantics':'nonzero runner fails ordinary step/job; later ordinary steps skip; upload always runs while job remains executable',
          'caps':{'job_minutes':15,'steps_minutes':[5,7,2],'owner_inner_default_seconds':60,'owner_host_seconds':300,
                  'owner_inner_stream_limit_bytes':4000000,'observer_inner_default_seconds':45,'observer_host_seconds':30,
                  'observer_inner_stream_byte_cap':None},
          'artifact_limitations':['Missing evidence is a warning; failure before creation remains in Actions logs.',
                                  'Whole job timeout/cancellation or unavailable upload service can prevent retained artifacts.']})
    def runners(self):
        owner=self.read(OWNER).decode();observer=self.read(OBSERVER).decode()
        for name,text in [(OWNER,owner),(OBSERVER,observer)]:
            ast.parse(text)
            (BASE/'runner-snapshots'/Path(name).name).parent.mkdir(parents=True,exist_ok=True)
            (BASE/'runner-snapshots'/Path(name).name).write_text(text)
        # No runner mutation or execution: these checks constrain glue to reviewed host-only code.
        for flag in ["'--release','17'","'-Xlint:all'","'-Werror'","'-proc:none'","'-classpath',empty","'-sourcepath',empty"]:
            check(flag in owner,'owner compiler closure flag '+flag)
        for flag in ["'--release', '17'","'-Xlint:all'","'-Werror'","'-proc:none'","'-classpath', str(empty)","'-sourcepath', str(empty)"]:
            check(flag in observer,'observer compiler closure flag '+flag)
        check(BARRIER in owner and DESCRIPTOR in owner and ROSTER in owner,'mandatory source paths')
        check("os.killpg(child.pid,signal.SIGKILL)" in owner and "os.killpg(process.pid, signal.SIGKILL)" in observer,'owned child cleanup')
        check("start_new_session=True" in owner and "start_new_session=True" in observer,'child groups')
        canonical=load(ROOT/'verification/android-private-owner-integration-implementation/candidate-4/source-map.json')
        cli=load(ROOT/'verification/android-private-owner-profile3-integration/candidate4-qualification/source-binding.json')['files']
        check(len(canonical)==309 and len(cli)==356,'frozen closure sizes')
        for name in ['.github/workflows/verify.yml','THIRD_PARTY.yml']:
            check(name not in canonical and name not in cli,'CI metadata entered frozen source closure')
        for name in (OWNER,OBSERVER):
            check(self.inputs[name]==canonical[name]==cli[name],'unchanged runner not exact frozen source')
        save(BASE/'frozen-boundary.json',{'canonical309_and_CLI356_metadata_paths_absent':True,
             'both_runners_unchanged_from_both_freezes':True,
             'native_runtime_execution_review':'New job only invokes frozen JVM host runners; no native/UI/capture invocation added.'})
    def receipts(self):
        original=load(LOCAL/'receipt.json');self.read(str((LOCAL/'receipt.json').relative_to(ROOT)))
        check(original['status']=='passed-local-host-recipe' and original['source_stable'],'local recipe disposition')
        check(not original['native_capture_UI_or_process_inventory'],'local pause compatibility')
        for name,value in original['source_bindings'].items():check(identity(self.read(name))==value,'root local source bind '+name)
        summary={};required={ROSTER,BARRIER,DESCRIPTOR,OWNER,OBSERVER}
        for record in original['commands']:
            lane=record['name'];folder=LOCAL/lane
            check(record['exit']==0 and record['child_reaped'],'local outer command status')
            for stream in ('stdout','stderr'):
                data=(LOCAL/(lane+'.'+stream)).read_bytes();check(identity(data)==record[stream],'local outer stream')
            receipt=load(folder/'receipt.json');commands=load(folder/'commands.json')
            check(receipt['status']=='passed-host-only' and not receipt['native_or_capture_processes_started_or_queried'],'inner host disposition')
            freeze=load(folder/('source-freeze.json' if lane=='observer' else 'source-map.json'));freeze=freeze.get('files',freeze)
            for name,value in freeze.items():
                check(identity(self.read(name))==value,'live retained source drift '+name)
                check(identity((folder/'inputs'/name).read_bytes())==value,'retained frozen input '+name)
                required.add(name)
            if lane=='observer':check(identity((folder/'source-freeze.json').read_bytes())==receipt['source_freeze'],'observer freeze receipt')
            for tool,value in receipt['tools'].items():check(identity(Path(tool).resolve().read_bytes())==value,'recorded actual JDK tool bytes')
            for command in commands:
                check(command['exit']==0 and command['child_reaped'] and not command.get('timed_out',False) and not command.get('timeout',False)
                      and not command.get('output_limit_exceeded',False),'inner raw command status')
                for stream in ('stdout','stderr'):check(identity((folder/(command['label']+'.'+stream)).read_bytes())==command[stream],'inner raw stream')
            compile=next(c for c in commands if c['label']=='compile')['argv']
            check(compile[1:6]==['--release','17','-Xlint:all','-Werror','-proc:none'],'exact host compile options')
            host=next(c for c in commands if c['label']=='host')['argv']
            check('-ea' in host and ('-Xmx128m' if lane=='observer' else '-Xmx256m') in host,'host JVM caps')
            version=(folder/'javac-version.stdout').read_text();check(version.strip()=='javac 27','actual local JDK version')
            output=(folder/'host.stdout').read_text().strip()
            expected={'orchestration':'cases=216 assertions=1101','renderer':'checks=14477','observer':'PASS 162 production Observer host cases'}[lane]
            check(expected in output and 'native runtime pending' in output,'honest exact host count')
            if lane!='observer':
                classes=load(folder/'class-map.json')
                for name,value in classes.items():
                    data=(folder/'classes'/name).read_bytes();check(identity(data)==value,'retained classes')
                    check(data[:4]==bytes.fromhex('cafebabe') and int.from_bytes(data[6:8],'big')==61,'Java17 classfile target')
                check(receipt['cleanup']['scratch_removed'] and receipt['cleanup']['children_reaped'],'owner cleanup')
                check(receipt['source_stable'],'owner unchanged sources')
            else:check(receipt['cleanup']['owned_scratch_removed'] and receipt['cleanup']['owned_children_reaped'],'observer cleanup')
            retained=BASE/'local-receipts'/lane;retained.mkdir(parents=True)
            for p in folder.iterdir():
                if p.is_file():shutil.copyfile(p,retained/p.name)
            for stream in ('stdout','stderr'):shutil.copyfile(LOCAL/(lane+'.'+stream),BASE/'local-receipts'/(lane+'.'+stream))
            summary[lane]={'source_members':len(freeze),'raw_commands':len(commands),'host_summary':output,
                 'actual_compiler':'OpenJDK27 --release17','Java17_runtime_evidence':False,
                 'retained_class_bytes_reverified':lane!='observer','observer_class_bytes_limit':'hashes retained but removed scratch classes cannot be reopened' if lane=='observer' else None}
        shutil.copyfile(LOCAL/'receipt.json',BASE/'local-receipts/root-receipt.json')
        save(BASE/'local-receipt-audit.json',summary)
        # Index visibility is read-only; root coordinates eventual canonical delivery.
        tracked=set(self.command('tracked-required-inputs',['/usr/bin/git','ls-files','-z','--',*sorted(required)]).decode().split('\0'))-{''}
        missing=sorted(required-tracked)
        check(BARRIER in missing and ROSTER in tracked and DESCRIPTOR in tracked,'delivery dependency state')
        save(BASE/'delivery-dependencies.json',{'required_paths':{name:self.inputs.get(name,identity((ROOT/name).read_bytes())) for name in sorted(required)},
            'currently_untracked_required_paths':missing,'mandatory_additional_delivery_path':BARRIER,
            'tracked_roster':ROSTER,'tracked_descriptor':DESCRIPTOR,
            'integration_disposition':'Root must deliver canonical native/CLI changes plus the frozen barrier map; metadata alone is insufficient.'})
        self.receipt.update(local_recipe_audited=True,local_raw_host_commands=17,local_host_summaries=summary,
                            mandatory_delivery_dependency=BARRIER,untracked_required_paths=missing)
    def main(self):
        try:
            self.workflow();self.runners();self.receipts()
            for name,value in self.inputs.items():check(identity((ROOT/name).read_bytes())==value,'postaudit source drift')
            save(BASE/'input-binding.json',self.inputs)
            self.receipt['status']='passed-bounded-CI-integration-review-conditional-on-complete-delivery-and-remote-CI'
        except BaseException as failure:
            self.receipt['failure']={'type':type(failure).__name__,'message':str(failure)}
            raise
        finally:
            self.receipt.update(commands=len(self.commands),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                pending=['Root complete canonical source and barrier-map delivery','Remote Ubuntu24.04/JDK17 execution and artifact receipt',
                         'Paused native/phone/UI/capture checks, immutable FieldLog, signing/store/operations/GA'],
                limitations=['Existing observer runner has time/memory caps but no raw stdout/stderr byte cap.',
                             'Observer class hashes are retained; removed raw classes are unavailable for independent reopening.',
                             'JDK launcher hashes do not bind every runtime library; raw runtime versions are retained.',
                             'No remote CI, product behavior rerun, native owner or whole-workflow acceptance claimed.'])
            save(BASE/'receipt.json',self.receipt)
            save(BASE/'commands.json',self.commands)

if __name__=='__main__':Review().main()
