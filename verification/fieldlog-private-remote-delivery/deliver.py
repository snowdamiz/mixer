#!/usr/bin/env python3
"""One authorized FieldLog delivery, with fresh exact-group command custody."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

EVIDENCE = Path(__file__).resolve().parent
APP = Path('/Users/andreyyurlov/Documents/dev/fieldlog')
PRODUCER = EVIDENCE.parent / 'fieldlog-public-sdk-next-flow' / 'receipt.json'
BASE = '82192341e6dd8c7ac2435dcf7cc4541f0af71e1f'
BASE_TREE = 'e09e055c6b96f33449bbda6c2dea1b717f5cb0b3'
REPO = 'snowdamiz/fieldlog'
PIN = 'd8c6965a277ca21e685f3ef9e0f68a7d59b46156'
ALLOWED = ['Package.swift', 'README.md', 'THIRD_PARTY.yml',
           'ios/FieldLog/ProjectDetail.swift',
           'Sources/FieldLogFeatures/TaskEditorPresentation.swift',
           'Tests/FieldLogTests/TaskEditorPresentationTests.swift',
           '.github/workflows/host.yml', 'scripts/verify-host-ci.py']
START = time.monotonic()
DEADLINE = START + 300
JOURNAL = EVIDENCE / 'commands.jsonl'
RECEIPT = {'schema': 1, 'startedAt': None, 'authorization':
           'User approved private snowdamiz/fieldlog creation, selected eight-file delivery and one manual host workflow.',
           'app': str(APP), 'repo': REPO, 'expectedBase': BASE,
           'expectedBaseTree': BASE_TREE, 'publicSDKPin': PIN,
           'limits': {'deliverySeconds': 300, 'commandSeconds': 55,
                      'pushSeconds': 120, 'outputBytes': 33554432},
           'nativeOrCompilerStartedLocally': False, 'dispatchAttempts': 0,
           'status': 'started', 'commands': []}
OUTPUT_TOTAL = 0


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def persist():
    target = EVIDENCE / 'receipt.json'
    temporary = EVIDENCE / 'receipt.tmp'
    with temporary.open('w') as stream:
        json.dump(RECEIPT, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(target)


def journal(item):
    with JOURNAL.open('a') as stream:
        stream.write(json.dumps(item) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def group_exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(label, args, allowed=(0,), seconds=55):
    global OUTPUT_TOTAL
    remaining = DEADLINE - time.monotonic() - 8
    require(remaining > 0, 'delivery budget exhausted before ' + label)
    seconds = min(seconds, remaining)
    record = {'label': label, 'command': args, 'cwd': str(APP),
              'startedAt': now(), 'secondsBound': seconds}
    log = EVIDENCE / f'{len(RECEIPT["commands"]):02d}-{label}.log'
    read_gate, write_gate = os.pipe()
    child = None
    admitted = False
    started = time.monotonic()
    failure = None
    environment = dict(os.environ)
    environment.update({'GIT_TERMINAL_PROMPT': '0', 'GH_PROMPT_DISABLED': '1',
                        'GH_PAGER': 'cat', 'GIT_PAGER': 'cat'})
    launcher = ('import os,sys; fd=int(sys.argv[1]); token=os.read(fd,1); '
                'os.close(fd); '
                'token==b"G" or sys.exit(125); '
                'os.execvp(sys.argv[2],sys.argv[2:])')
    try:
        with log.open('wb') as output:
            child = subprocess.Popen([sys.executable, '-B', '-c', launcher,
                                      str(read_gate)] + args,
                                     cwd=APP, env=environment,
                                     stdin=subprocess.DEVNULL, stdout=output,
                                     stderr=subprocess.STDOUT,
                                     pass_fds=(read_gate,), start_new_session=True)
            os.close(read_gate)
            read_gate = -1
            record.update({'pid': child.pid, 'pgid': os.getpgid(child.pid)})
            require(record['pgid'] == child.pid, 'fresh group identity mismatch')
            journal({'event': 'owned-child-before-admission', **record})
            os.write(write_gate, b'G')
            admitted = True
            os.close(write_gate)
            write_gate = -1
            end = started + seconds
            while child.poll() is None:
                if time.monotonic() >= end:
                    raise TimeoutError(label + ' timed out')
                require(log.stat().st_size + OUTPUT_TOTAL <= 33554432,
                        'aggregate output bound exceeded')
                time.sleep(0.05)
    except BaseException as error:
        failure = error
    finally:
        for descriptor in (read_gate, write_gate):
            if descriptor >= 0:
                os.close(descriptor)
        if child is not None:
            cleanup_started = time.monotonic()
            try:
                if not admitted:
                    child.wait(timeout=2)
                if group_exists(child.pid):
                    os.killpg(child.pid, signal.SIGTERM)
                    until = time.monotonic() + 2
                    while group_exists(child.pid) and time.monotonic() < until:
                        child.poll()
                        time.sleep(0.05)
                if group_exists(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
                until = time.monotonic() + 2
                while group_exists(child.pid) and time.monotonic() < until:
                    time.sleep(0.05)
                record['cleanup'] = {'directChildReaped': child.returncode is not None,
                                     'exactOwnedGroupAbsent': not group_exists(child.pid),
                                     'outputTransport': 'closed regular file; no pipe descendants',
                                     'seconds': round(time.monotonic() - cleanup_started, 3)}
            except BaseException as error:
                record['cleanup'] = {'error': repr(error)}
                if failure is None:
                    failure = error
            record['exitCode'] = child.returncode
        data = log.read_bytes() if log.exists() else b''
        OUTPUT_TOTAL += len(data)
        record.update({'endedAt': now(), 'wallSeconds': round(time.monotonic()-started, 3),
                       'log': log.name, 'outputBytes': len(data),
                       'outputSHA256': hashlib.sha256(data).hexdigest()})
        if failure:
            record['error'] = repr(failure)
        RECEIPT['commands'].append(record)
        journal({'event': 'command-finalized', **record})
        persist()
    if failure:
        raise failure
    require(record.get('cleanup', {}).get('exactOwnedGroupAbsent') is True,
            'owned cleanup not verified: ' + label)
    require(record['exitCode'] in allowed, f'{label} failed: exit {record["exitCode"]}')
    return data.decode('utf-8', errors='replace').rstrip('\r\n'), record['exitCode']


def git(label, *args, **kwargs):
    return command(label, ['git', *args], **kwargs)[0]


def metadata(label):
    output, code = command(label, ['gh', 'api', 'repos/' + REPO,
                           '--jq', '{id,full_name,private,owner:.owner.login,size,default_branch,pushed_at,html_url}'],
                           allowed=(0, 1))
    if code:
        require('(HTTP 404)' in output, 'repository metadata failed without confirmed 404')
        return None
    result = json.loads(output)
    require(result['full_name'] == REPO and result['owner'] == 'snowdamiz',
            'unexpected repository ownership')
    require(result['private'] is True, 'destination is not private')
    return result


def main():
    RECEIPT['startedAt'] = now()
    persist()
    RECEIPT['tools'] = {'python': sys.version,
                        'git': git('git-version', '--version'),
                        'gh': command('gh-version', ['gh', '--version'])[0]}
    require(git('base-revision', 'rev-parse', 'HEAD') == BASE, 'base revision changed')
    require(git('base-tree', 'rev-parse', 'HEAD^{tree}') == BASE_TREE, 'base tree changed')
    RECEIPT['branch'] = git('branch', 'symbolic-ref', '--short', 'HEAD')
    require(RECEIPT['branch'] == 'main', 'unexpected local branch')
    require(git('initial-index', 'diff', '--cached', '--name-only') == '', 'preexisting staged changes')
    status = git('initial-status', 'status', '--porcelain=v1', '--untracked-files=all')
    require(set(line[3:] for line in status.splitlines()) == set(ALLOWED),
            'worktree paths differ from eight-file authorization')
    RECEIPT['initialStatus'] = status
    expected = {entry['path']: entry['sha256'] for entry in json.loads(PRODUCER.read_text())['currentSourceFiles']}
    require(set(expected) == set(ALLOWED), 'producer scope differs')
    RECEIPT['sourceFiles'] = []
    for path in ALLOWED:
        data = (APP / path).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        require(digest == expected[path], 'prepared source hash changed: ' + path)
        RECEIPT['sourceFiles'].append({'path': path, 'bytes': len(data), 'sha256': digest})
    require(PIN in (APP / 'Package.swift').read_text(), 'manifest immutable pin absent')
    tracked = git('tracked-files', 'ls-files', '-z').split('\x00')
    untouched = {path: hashlib.sha256((APP / path).read_bytes()).hexdigest()
                 for path in tracked if path and path not in ALLOWED and (APP / path).is_file()}
    RECEIPT['untouchedTrackedFileHashes'] = untouched
    git('diff-check', 'diff', '--check')
    git('source-diff', 'diff', '--', *ALLOWED)
    require(git('initial-remotes', 'remote') == '', 'remote appeared before authorized creation')
    user = json.loads(command('github-login', ['gh', 'api', 'user', '--jq', '{login,id}'])[0])
    RECEIPT['githubUser'] = user
    require(user['login'] == 'snowdamiz', 'unexpected authenticated GitHub login')
    repo = metadata('repository-before')
    RECEIPT['repositoryBefore'] = repo
    if repo is not None:
        refs = command('existing-remote-refs', ['git', 'ls-remote', 'https://github.com/' + REPO + '.git'])[0]
        require(refs == '' and repo['size'] == 0, 'existing destination is unexpectedly nonempty')
        RECEIPT['createdRepository'] = False
    else:
        created = json.loads(command('create-private-repository', ['gh', 'api', '--method', 'POST',
                             'user/repos', '-f', 'name=fieldlog', '-F', 'private=true', '-F', 'auto_init=false',
                             '--jq', '{id,full_name,private,owner:.owner.login,html_url}'])[0])
        require(created['full_name'] == REPO and created['private'] is True and
                created['owner'] == 'snowdamiz', 'created destination mismatch')
        RECEIPT['createdRepository'] = created
    RECEIPT['repositoryAfterCreate'] = metadata('repository-after-create')
    require(git('pre-origin-remotes', 'remote') == '', 'remote changed during delivery')
    git('add-origin', 'remote', 'add', 'origin', 'https://github.com/' + REPO + '.git')
    require(git('verify-origin', 'remote', 'get-url', 'origin') == 'https://github.com/' + REPO + '.git',
            'origin mismatch')
    git('stage-eight-paths', 'add', '--', *ALLOWED)
    staged = git('staged-paths', 'diff', '--cached', '--name-only').splitlines()
    require(set(staged) == set(ALLOWED), 'staged scope differs')
    git('staged-diff-check', 'diff', '--cached', '--check')
    git('staged-stat', 'diff', '--cached', '--stat')
    for path in ALLOWED:
        blob = command('index-' + str(ALLOWED.index(path)), ['git', 'show', ':' + path])[0]
        # Decode is only for the text display command; compare exact bytes from its retained log.
        retained = EVIDENCE / RECEIPT['commands'][-1]['log']
        require(hashlib.sha256(retained.read_bytes()).hexdigest() == expected[path], 'index content changed: ' + path)
    git('commit-eight-paths', '-c', 'core.hooksPath=/dev/null', 'commit', '-m',
        'Wire shared task editor and manual host verification', '-m',
        'Host tests remain pending until the single manual CI run completes. Native runtime qualification is pending.')
    head = git('selected-commit', 'rev-parse', 'HEAD')
    tree = git('selected-tree', 'rev-parse', 'HEAD^{tree}')
    RECEIPT.update({'commit': head, 'tree': tree})
    require(git('commit-parent', 'rev-parse', 'HEAD^') == BASE, 'commit parent mismatch')
    require(set(git('committed-paths', 'diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines()) == set(ALLOWED),
            'committed path scope differs')
    require(git('after-commit-status', 'status', '--porcelain=v1', '--untracked-files=all') == '', 'app status changed')
    command('push-main', ['git', '-c', 'core.hooksPath=/dev/null', 'push', '--porcelain', 'origin',
                         'HEAD:refs/heads/main'], seconds=120)
    remote = git('verify-remote-main', 'ls-remote', '--exit-code', 'origin', 'refs/heads/main')
    require(remote.split()[0] == head, 'remote main differs from selected commit')
    RECEIPT['remoteRef'] = remote
    RECEIPT['repositoryBeforeDispatch'] = metadata('repository-before-dispatch')
    workflow = json.loads(command('workflow-registered', ['gh', 'api', 'repos/' + REPO + '/actions/workflows/host.yml',
                                '--jq', '{id,name,path,state,html_url}'])[0])
    require(workflow['path'] == '.github/workflows/host.yml' and workflow['state'] == 'active', 'workflow mismatch')
    RECEIPT['workflow'] = workflow
    RECEIPT['dispatchAttempts'] = 1
    RECEIPT['dispatchStartedAt'] = now()
    persist()
    command('dispatch-once', ['gh', 'workflow', 'run', 'host.yml', '--repo', REPO, '--ref', 'main'])
    RECEIPT['dispatchAccepted'] = True
    for index, pause in enumerate((2, 5, 10)):
        require(DEADLINE - time.monotonic() > pause + 8, 'budget exhausted before run observation')
        time.sleep(pause)
        runs = json.loads(command('observe-dispatched-run-' + str(index), ['gh', 'api',
                          'repos/' + REPO + '/actions/runs?event=workflow_dispatch&head_sha=' + head + '&per_page=10',
                          '--jq', '{total_count,workflow_runs:[.workflow_runs[]|{id,html_url,head_sha,head_branch,event,status,conclusion,run_attempt,workflow_id,path,created_at}]}'])[0])
        selected = [run for run in runs['workflow_runs'] if run['head_sha'] == head and
                    run['workflow_id'] == workflow['id'] and run['event'] == 'workflow_dispatch']
        require(len(selected) <= 1, 'ambiguous multiple matching manual runs')
        if selected:
            RECEIPT['run'] = selected[0]
            break
    require('run' in RECEIPT, 'dispatch accepted but exact run not yet observed')
    for path, digest in untouched.items():
        require(hashlib.sha256((APP / path).read_bytes()).hexdigest() == digest, 'untouched tracked source changed: ' + path)
    require(git('final-local-head', 'rev-parse', 'HEAD') == head, 'local head changed')
    require(git('final-app-status', 'status', '--porcelain=v1', '--untracked-files=all') == '', 'final app is dirty')
    RECEIPT['status'] = 'private-delivery-complete-one-manual-host-run-observed'


try:
    main()
except BaseException as error:
    RECEIPT['status'] = 'stopped-with-error'
    RECEIPT['error'] = repr(error)
    raise
finally:
    RECEIPT['endedAt'] = now()
    RECEIPT['wallSeconds'] = round(time.monotonic() - START, 3)
    RECEIPT['outputBytes'] = OUTPUT_TOTAL
    persist()
    print(json.dumps({key: RECEIPT.get(key) for key in
                      ('status', 'error', 'commit', 'tree', 'createdRepository',
                       'dispatchAttempts', 'dispatchAccepted', 'run', 'wallSeconds')}), flush=True)
