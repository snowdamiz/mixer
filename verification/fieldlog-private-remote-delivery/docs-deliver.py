#!/usr/bin/env python3
"""Authorized two-file documentation correction; no workflow dispatch or compiler."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
APP = Path('/Users/andreyyurlov/Documents/dev/fieldlog')
BASE = '70f3aa1d28f29e7c327a17fd46199480d41ca749'
TREE = '8d962e2f3b52aad4b417f98b5553bc5762fde908'
REPO = 'snowdamiz/fieldlog'
DOCS = ['README.md', 'THIRD_PARTY.yml']
START = time.monotonic()
DEADLINE = START+300
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
PREFIX = 'docs-'+STAMP
JOURNAL = ROOT / (PREFIX+'-commands.jsonl')
RECEIPT = {'schema': 1, 'prefix': PREFIX, 'baseRevision': BASE, 'baseTree': TREE,
           'app': str(APP), 'repo': REPO, 'filesAuthorized': DOCS, 'commands': [],
           'status': 'started', 'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'authorization': 'Root delegated the user-authorized private README and qualification correction, two-file commit and nonforce push.',
           'limits': {'aggregateSeconds':300,'commandSeconds':55,'pushSeconds':120,'outputBytes':33554432},
           'noCompilerNativeBillingOrDispatchActions': True, 'priorSealedEvidenceModified': False}
TOTAL_OUTPUT = 0


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def append(item):
    with JOURNAL.open('a') as stream:
        stream.write(json.dumps(item)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def run(label, args, seconds=55):
    global TOTAL_OUTPUT
    limit=min(seconds,DEADLINE-time.monotonic()-8)
    require(limit>0,'delivery aggregate budget exhausted')
    record={'label':label,'command':args,'cwd':str(APP),'secondsBound':limit,
            'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    path=ROOT/(PREFIX+f'-{len(RECEIPT["commands"]):02d}-'+label+'.log')
    gate_read,gate_write=os.pipe()
    child=None
    admitted=False
    failure=None
    began=time.monotonic()
    env=dict(os.environ,GH_PROMPT_DISABLED='1',GH_PAGER='cat',GIT_PAGER='cat',GIT_TERMINAL_PROMPT='0')
    launcher=('import os,sys; fd=int(sys.argv[1]); t=os.read(fd,1); os.close(fd); '
              't==b"G" or sys.exit(125); os.execvp(sys.argv[2],sys.argv[2:])')
    try:
        with path.open('xb') as output:
            child=subprocess.Popen([sys.executable,'-B','-c',launcher,str(gate_read)]+args,
                                   cwd=APP,env=env,stdin=subprocess.DEVNULL,stdout=output,
                                   stderr=subprocess.STDOUT,start_new_session=True,pass_fds=(gate_read,))
            os.close(gate_read)
            gate_read=-1
            record.update(pid=child.pid,pgid=os.getpgid(child.pid))
            require(record['pgid']==child.pid,'fresh exact group mismatch')
            append({'event':'owned-child-before-admission',**record})
            os.write(gate_write,b'G')
            admitted=True
            os.close(gate_write)
            gate_write=-1
            while child.poll() is None:
                require(time.monotonic()-began<limit,label+' timeout')
                require(path.stat().st_size+TOTAL_OUTPUT<=33554432,'aggregate output bound exceeded')
                time.sleep(0.05)
    except BaseException as error:
        failure=error
    finally:
        for descriptor in (gate_read,gate_write):
            if descriptor>=0:
                os.close(descriptor)
        if child is not None:
            try:
                if not admitted:
                    child.wait(timeout=2)
                if exists(child.pid):
                    os.killpg(child.pid,signal.SIGTERM)
                    until=time.monotonic()+2
                    while exists(child.pid) and time.monotonic()<until:
                        child.poll()
                        time.sleep(0.05)
                if exists(child.pid):
                    os.killpg(child.pid,signal.SIGKILL)
                child.wait(timeout=2)
                until=time.monotonic()+2
                while exists(child.pid) and time.monotonic()<until:
                    time.sleep(0.05)
                record['cleanup']={'directChildReaped':child.returncode is not None,
                                   'exactOwnedGroupAbsent':not exists(child.pid),
                                   'outputTransport':'closed regular file'}
                record['exitCode']=child.returncode
            except BaseException as error:
                record['cleanup']={'error':repr(error)}
                failure=failure or error
        data=path.read_bytes() if path.exists() else b''
        TOTAL_OUTPUT+=len(data)
        record.update(wallSeconds=round(time.monotonic()-began,3),log=path.name,
                      outputBytes=len(data),outputSHA256=hashlib.sha256(data).hexdigest())
        if failure:
            record['error']=repr(failure)
        RECEIPT['commands'].append(record)
        append({'event':'command-finalized',**record})
    if failure:
        raise failure
    require(record.get('cleanup',{}).get('exactOwnedGroupAbsent'),'cleanup ambiguity')
    require(record['exitCode']==0,label+' failed')
    return data.decode('utf-8',errors='replace').rstrip('\r\n')


def git(label,*args,**kwargs):
    return run(label,['git',*args],**kwargs)


def verify_bindings(previous):
    for source in previous['sourceFiles']:
        if source['path'] not in DOCS:
            require(hashlib.sha256((APP/source['path']).read_bytes()).hexdigest()==source['sha256'],
                    'protected source changed: '+source['path'])
    for path,digest in previous['untouchedTrackedFileHashes'].items():
        require(hashlib.sha256((APP/path).read_bytes()).hexdigest()==digest,'other tracked file changed: '+path)


def edit_docs():
    readme=APP/'README.md'
    text=readme.read_text()
    old='''See `verification/native-baseline-2026-10-22.json` for exact observed evidence and
`scripts/verify.sh` for the separate repository's local CI entrypoint. No hosted
CI execution or customer activity is claimed.

`.github/workflows/host.yml` is a prepared manual host-only workflow; it has not
run. Once a separate FieldLog remote and dispatch are authorized, it invokes
`scripts/verify-host-ci.py` on one disposable macOS runner. The remote-only script
records each fresh child PID/PGID before admitting its command, reserves cleanup
time, and requires direct-child reaping, exact owned-group absence and output
EOF. It stops on ambiguous identity/cleanup and does not inspect previously held
local resources. The total runner budget is 750 seconds, captured output is capped
at 32 MiB, and host tests use two compiler jobs. No native builds or runtimes run.

The workflow fetches only the existing public Mixer commit into a transient CI
mirror and keeps the declared remote URL and immutable pin. It binds the actual
consumed SDK commit/tree, all tracked app source and test results. A lock refresh
may change only `originHash`, which is reported with before/after bytes; changed
dependency identity/location/revision fails. This is development verification
through a private CI mirror, not new published-release-package qualification.
The app currently has no configured Git remote. No remote creation, push or
workflow dispatch is implied by these prepared files.
'''
    new='''See `verification/native-baseline-2026-10-22.json` for exact observed evidence and
`scripts/verify.sh` for the separate repository's local CI entrypoint. No customer
activity is claimed.

The private repository [snowdamiz/fieldlog](https://github.com/snowdamiz/fieldlog)
is configured as `origin`. The shared task-editor and manual host-CI code was
delivered in commit `70f3aa1d28f29e7c327a17fd46199480d41ca749`.
The single manual [host workflow run 40744921829](https://github.com/snowdamiz/fieldlog/actions/runs/40744921829)
targeted that exact commit and failed before runner assignment because GitHub
reported failed account payments or a spending limit requiring an increase.
**0 of 26 expected host test functions executed; no artifacts were produced.**
No compiler, public SDK fetch, lock refresh or runner cleanup executed in that
attempt. The earlier local Swift dependency-fetch attempt still has unverified
cleanup; its held resources have not been inspected or reused.

`.github/workflows/host.yml` is a manual host-only development workflow. When a
runner is admitted, it invokes `scripts/verify-host-ci.py` on one disposable macOS
runner. The remote-only script records each fresh child PID/PGID before admitting
its command, reserves cleanup time, and requires direct-child reaping, exact
owned-group absence and output EOF. It stops on ambiguous identity/cleanup and
does not inspect previously held local resources. The total runner budget is
750 seconds, captured output is capped at 32 MiB, and host tests use two compiler
jobs. It does not invoke native builds or runtimes. These runner safeguards and
the current host tests remain unexecuted in CI.

The workflow is designed to fetch only the existing public Mixer commit into a
transient CI mirror while keeping the declared remote URL and immutable pin. It
binds the actual consumed SDK commit/tree, all tracked app source and test
results. A lock refresh may change only `originHash`, which is reported with
before/after bytes; changed dependency identity/location/revision fails. This
development verification through a private CI mirror remains pending and does
not establish new published-release-package qualification.
'''
    require(text.count(old)==1,'README target text changed')
    readme.write_text(text.replace(old,new))
    third_party=APP/'THIRD_PARTY.yml'
    text=third_party.read_text()
    old='    qualification: Development API only; previous MixerCore host/simulator evidence retained, current MixerUI presentation tests pending after public dependency fetch timeout, full dogfood gates open\n'
    new='    qualification: Development API only; private origin snowdamiz/fieldlog configured with code commit 70f3aa1d28f29e7c327a17fd46199480d41ca749; manual run 40744921829 blocked by GitHub billing/spending before runner assignment (0 of 26 host tests executed, no artifacts); earlier local Swift fetch cleanup remains unverified; previous MixerCore host/simulator evidence retained and full dogfood gates open\n'
    require(text.count(old)==1,'qualification target changed')
    third_party.write_text(text.replace(old,new))


try:
    previous=json.loads((ROOT/'receipt.json').read_text())
    require(git('base','rev-parse','HEAD')==BASE,'app base changed')
    require(git('base-tree','rev-parse','HEAD^{tree}')==TREE,'app tree changed')
    require(git('initial-status','status','--porcelain=v1','--untracked-files=all')=='','preexisting app changes')
    require(git('initial-index','diff','--cached','--name-only')=='','preexisting staged changes')
    require(git('origin','remote','get-url','origin')=='https://github.com/'+REPO+'.git','unexpected origin')
    remote=git('remote-before','ls-remote','--exit-code','origin','refs/heads/main')
    require(remote.split()[0]==BASE,'remote main changed')
    metadata=json.loads(run('private-destination',['gh','api','repos/'+REPO,'--jq',
                              '{id,full_name,private,owner:.owner.login,html_url}']))
    require(metadata['id']==1437474527 and metadata['full_name']==REPO and metadata['private'] is True and
            metadata['owner']=='snowdamiz','private destination mismatch')
    RECEIPT['repository']=metadata
    RECEIPT['tools']={'python':sys.version,'git':git('git-version','--version'),'gh':run('gh-version',['gh','--version'])}
    verify_bindings(previous)
    for source in previous['sourceFiles']:
        if source['path'] in DOCS:
            require(hashlib.sha256((APP/source['path']).read_bytes()).hexdigest()==source['sha256'],
                    'documentation changed before correction')
    RECEIPT['beforeFiles']=[{'path':p,'sha256':hashlib.sha256((APP/p).read_bytes()).hexdigest()} for p in DOCS]
    edit_docs()
    git('diff-check','diff','--check')
    require(set(git('changed-paths','diff','--name-only').splitlines())==set(DOCS),'docs scope mismatch')
    git('docs-diff','diff','--',*DOCS)
    git('stage-two-docs','add','--',*DOCS)
    require(set(git('staged-paths','diff','--cached','--name-only').splitlines())==set(DOCS),'staged scope mismatch')
    git('staged-diff-check','diff','--cached','--check')
    for index,path in enumerate(DOCS):
        git('index-'+str(index),'show',':'+path)
        raw=(ROOT/RECEIPT['commands'][-1]['log']).read_bytes()
        require(raw==(APP/path).read_bytes(),'index differs from reviewed documentation')
    verify_bindings(previous)
    RECEIPT['afterFiles']=[{'path':p,'sha256':hashlib.sha256((APP/p).read_bytes()).hexdigest()} for p in DOCS]
    git('commit-docs','-c','core.hooksPath=/dev/null','commit','-m',
        'Document private delivery and blocked host CI attempt')
    head=git('doc-commit','rev-parse','HEAD')
    RECEIPT.update(commit=head,tree=git('doc-tree','rev-parse','HEAD^{tree}'))
    require(git('doc-parent','rev-parse','HEAD^')==BASE,'documentation parent mismatch')
    require(set(git('committed-paths','diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())==set(DOCS),
            'commit contains more than authorized documentation')
    require(git('after-commit-status','status','--porcelain=v1','--untracked-files=all')=='','app dirty after docs commit')
    run('push-docs',['git','-c','core.hooksPath=/dev/null','push','--porcelain','origin','HEAD:refs/heads/main'],seconds=120)
    remote=git('remote-after','ls-remote','--exit-code','origin','refs/heads/main')
    require(remote.split()[0]==head,'documentation remote head mismatch')
    RECEIPT['verifiedRemoteRef']=remote
    verify_bindings(previous)
    require(git('final-status','status','--porcelain=v1','--untracked-files=all')=='','final app status changed')
    RECEIPT.update(status='two-file-documentation-delivered-no-redispatch',protectedCodeAndOtherTrackedFilesUnchanged=True,
                   priorRunID=40744921829,priorRunCodeCommit=BASE,priorRunObservedTests=0,priorRunExpectedTests=26,
                   priorRunArtifacts=0,originalLocalSwiftCleanup='unverified and unprobed')
except BaseException as error:
    RECEIPT['status']='stopped-with-error'
    RECEIPT['error']=repr(error)
    raise
finally:
    RECEIPT.update(endedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   wallSeconds=round(time.monotonic()-START,3),outputBytes=TOTAL_OUTPUT,
                   helperSHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    output=ROOT/(PREFIX+'-receipt.json')
    with output.open('x') as stream:
        json.dump(RECEIPT,stream,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({key:RECEIPT.get(key) for key in ('status','error','commit','tree','wallSeconds')}|
                     {'receipt':str(output)}),flush=True)
