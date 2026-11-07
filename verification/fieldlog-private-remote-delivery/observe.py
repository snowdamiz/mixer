#!/usr/bin/env python3
"""Bounded read-only GitHub observation; never executes downloaded evidence."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parent
REPO = 'snowdamiz/fieldlog'
RUN = 40744921829
HEAD = '70f3aa1d28f29e7c327a17fd46199480d41ca749'
START = time.monotonic()
DEADLINE = START + 180
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
RECORDS = []


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def save():
    path = ROOT / ('observation-' + STAMP + '.json')
    with path.open('w') as stream:
        json.dump({'repo': REPO, 'runID': RUN, 'expectedHead': HEAD,
                   'connectorFallback': 'GitHub plugin jobs returned 404 for new private repo',
                   'wallSeconds': round(time.monotonic()-START, 3), 'commands': RECORDS}, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def exists(group):
    try:
        os.killpg(group, 0)
        return True
    except ProcessLookupError:
        return False


def run(label, argv, binary=False):
    remaining = min(55, DEADLINE-time.monotonic()-8)
    require(remaining > 0, 'observer aggregate bound exhausted')
    record = {'label': label, 'command': argv, 'cwd': str(ROOT), 'secondsBound': remaining,
              'startedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    destination = ROOT / (STAMP + '-' + label + ('.zip' if binary else '.log'))
    gate_read, gate_write = os.pipe()
    child = None
    failure = None
    admitted = False
    began = time.monotonic()
    env = dict(os.environ, GH_PROMPT_DISABLED='1', GH_PAGER='cat', GIT_TERMINAL_PROMPT='0')
    launcher = ('import os,sys; fd=int(sys.argv[1]); t=os.read(fd,1); os.close(fd); '
                't==b"G" or sys.exit(125); os.execvp(sys.argv[2],sys.argv[2:])')
    stderr_path = ROOT / (STAMP + '-' + label + '.stderr.log')
    try:
        with destination.open('wb') as stdout, stderr_path.open('wb') as stderr:
            child = subprocess.Popen([sys.executable, '-B', '-c', launcher, str(gate_read)] + argv,
                                     cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                     stdout=stdout, stderr=stderr,
                                     start_new_session=True, pass_fds=(gate_read,))
            os.close(gate_read)
            gate_read = -1
            record.update(pid=child.pid, pgid=os.getpgid(child.pid))
            require(record['pgid'] == child.pid, 'fresh observer group mismatch')
            RECORDS.append(record)
            save()  # Persist child identity before admission and waiting.
            os.write(gate_write, b'G')
            admitted = True
            os.close(gate_write)
            gate_write = -1
            while child.poll() is None:
                require(time.monotonic()-began < remaining, label + ' command timeout')
                require(destination.stat().st_size + stderr_path.stat().st_size <= 33554432,
                        'observer output ceiling exceeded')
                time.sleep(0.05)
    except BaseException as error:
        failure = error
    finally:
        for descriptor in (gate_read, gate_write):
            if descriptor >= 0:
                os.close(descriptor)
        if child is not None:
            try:
                if not admitted:
                    child.wait(timeout=2)
                if exists(child.pid):
                    os.killpg(child.pid, signal.SIGTERM)
                    until = time.monotonic()+2
                    while exists(child.pid) and time.monotonic() < until:
                        child.poll()
                        time.sleep(0.05)
                if exists(child.pid):
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
                until = time.monotonic()+2
                while exists(child.pid) and time.monotonic() < until:
                    time.sleep(0.05)
                record['cleanup'] = {'directChildReaped': child.returncode is not None,
                                     'exactOwnedGroupAbsent': not exists(child.pid),
                                     'outputTransport': 'closed regular files'}
                record['exitCode'] = child.returncode
            except BaseException as error:
                record['cleanup'] = {'error': repr(error)}
                failure = failure or error
        if record not in RECORDS:
            RECORDS.append(record)
        record['wallSeconds'] = round(time.monotonic()-began, 3)
        record['outputs'] = []
        for path in (destination, stderr_path):
            if path.exists():
                data = path.read_bytes()
                record['outputs'].append({'path': path.name, 'bytes': len(data),
                                          'sha256': hashlib.sha256(data).hexdigest()})
        if failure:
            record['error'] = repr(failure)
        save()
    if failure:
        raise failure
    require(record.get('cleanup', {}).get('exactOwnedGroupAbsent'), 'observer cleanup ambiguous')
    require(record['exitCode'] == 0, 'GitHub CLI read failed: ' + label)
    return destination


def api(label, endpoint, selector):
    return json.loads(run(label, ['gh', 'api', endpoint, '--jq', selector]).read_text())


try:
    prefix = 'repos/' + REPO + '/actions'
    if len(sys.argv) == 1 or sys.argv[1] == 'snapshot':
        state = api('run', prefix + '/runs/' + str(RUN),
                    '{id,head_sha,head_branch,event,status,conclusion,run_attempt,workflow_id,path,created_at,updated_at,run_started_at,html_url}')
        require(state['head_sha'] == HEAD and state['event'] == 'workflow_dispatch' and state['run_attempt'] == 1,
                'workflow identity or attempt changed')
        jobs = api('jobs', prefix + '/runs/' + str(RUN) + '/jobs',
                   '{total_count,jobs:[.jobs[]|{id,name,status,conclusion,run_id,html_url,started_at,completed_at,runner_name,runner_group_name,labels,steps}]}')
        artifacts = api('artifacts', prefix + '/runs/' + str(RUN) + '/artifacts',
                        '{total_count,artifacts:[.artifacts[]|{id,name,size_in_bytes,expired,created_at,updated_at,digest,workflow_run}]}')
        print(json.dumps({'run': state, 'jobs': jobs, 'artifacts': artifacts}), flush=True)
    elif sys.argv[1] == 'diagnose':
        checks = api('checks', 'repos/' + REPO + '/commits/' + HEAD + '/check-runs',
                     '{total_count,check_runs:[.check_runs[]|{id,name,status,conclusion,details_url,output:{title:.output.title,summary:.output.summary,text:.output.text,annotations_count:.output.annotations_count}}]}')
        annotations = []
        for check in checks['check_runs']:
            if check['output']['annotations_count']:
                require(check['output']['annotations_count'] <= 100, 'annotation bound')
                annotations.append({'checkRunID': check['id'], 'annotations':
                    api('annotations-' + str(check['id']), 'repos/' + REPO + '/check-runs/' + str(check['id']) + '/annotations?per_page=100',
                        '[.[]|{path,start_line,end_line,annotation_level,title,message,raw_details}]')})
        print(json.dumps({'checks': checks, 'annotations': annotations}), flush=True)
    elif sys.argv[1] == 'artifact':
        artifact_id = int(sys.argv[2])
        metadata = api('artifact-metadata', prefix + '/artifacts/' + str(artifact_id),
                       '{id,name,size_in_bytes,expired,digest,workflow_run}')
        require(metadata['workflow_run']['id'] == RUN and metadata['workflow_run']['head_sha'] == HEAD,
                'artifact run/head mismatch')
        require(not metadata['expired'] and metadata['size_in_bytes'] <= 33554432, 'artifact size/expiry bound')
        archive = run('artifact-download', ['gh', 'api', prefix + '/artifacts/' + str(artifact_id) + '/zip'], binary=True)
        raw = archive.read_bytes()
        require(len(raw) <= 33554432, 'compressed artifact bound')
        digest = metadata.get('digest')
        if digest:
            require(digest == 'sha256:' + hashlib.sha256(raw).hexdigest(), 'artifact digest mismatch')
        output = ROOT / ('artifact-' + str(artifact_id))
        require(not output.exists(), 'refuse to overwrite extracted artifact')
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            require(len(entries) <= 1000 and sum(item.file_size for item in entries) <= 67108864,
                    'artifact expanded file/byte ceiling')
            names = set()
            for item in entries:
                path = Path(item.filename)
                require(item.filename not in names, 'duplicate archive path')
                names.add(item.filename)
                require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename,
                        'unsafe archive path')
                require((item.external_attr >> 16) & 0o170000 != 0o120000, 'archive symlink rejected')
                require(not item.flag_bits & 1, 'encrypted artifact rejected')
            output.mkdir()
            for item in entries:
                path = output / item.filename
                if item.is_dir():
                    path.mkdir(parents=True, exist_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(item) as source, path.open('xb') as destination:
                        remaining = item.file_size
                        while remaining:
                            block = source.read(min(65536, remaining))
                            require(block, 'truncated archive entry')
                            destination.write(block)
                            remaining -= len(block)
                        require(source.read(1) == b'', 'archive entry expanded beyond claimed bound')
                    path.chmod(0o600)
        files = [{'path': str(path.relative_to(ROOT)), 'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
                 for path in sorted(output.rglob('*')) if path.is_file()]
        manifest = {'artifact': metadata, 'zipSHA256': hashlib.sha256(raw).hexdigest(),
                    'untrustedEvidenceOnlyNoExecution': True, 'files': files}
        (ROOT / ('artifact-' + str(artifact_id) + '-manifest.json')).write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps(manifest), flush=True)
    else:
        raise RuntimeError('unsupported read-only observation mode')
finally:
    save()
