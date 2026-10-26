#!/usr/bin/env python3
"""Bounded owned process groups; logs preserve failed/partial output."""
import datetime, hashlib, json, os, pathlib, shutil, signal, subprocess, sys, time
BASE = pathlib.Path(__file__).resolve().parent

def run(label, argv, timeout=240, cwd=None, env=None):
    folder = BASE / 'commands' / (datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + label)
    folder.mkdir(parents=True)
    meta = {'argv': list(map(str, argv)), 'cwd': str(cwd or pathlib.Path.cwd()), 'deadline_seconds': timeout,
            'start': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    binding = BASE / 'source-binding.json'
    if binding.is_file(): meta['source_binding_sha256'] = hashlib.sha256(binding.read_bytes()).hexdigest()
    executable = pathlib.Path(shutil.which(str(argv[0]), path=(env or os.environ).get('PATH')) or str(argv[0])).resolve()
    if executable.is_file():
        meta['executable'] = {'path': str(executable), 'sha256': hashlib.sha256(executable.read_bytes()).hexdigest()}
    (folder / 'command.json').write_text(json.dumps(meta, indent=2)+'\n')
    start = time.monotonic()
    with (folder / 'output.txt').open('wb') as output:
        p = subprocess.Popen(meta['argv'], cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = p.wait(timeout=timeout)
            meta['timed_out'] = False
        except subprocess.TimeoutExpired:
            meta['timed_out'] = True
            os.killpg(p.pid, signal.SIGTERM)
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL); p.wait()
            code = p.returncode
        # Reap any child group before the caller can clean owned scratch.
        try:
            os.killpg(p.pid, signal.SIGTERM)
            until = time.monotonic() + 5
            while time.monotonic() < until:
                try: os.killpg(p.pid, 0)
                except ProcessLookupError: break
                time.sleep(0.02)
            else:
                os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError: pass
    meta['owned_group_cleanup'] = 'parent reaped; remaining owned group signaled before return'
    meta.update(exit_code=code, elapsed_seconds=time.monotonic()-start,
                output_sha256=hashlib.sha256((folder/'output.txt').read_bytes()).hexdigest())
    (folder / 'result.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(str(folder), flush=True)
    print((folder/'output.txt').read_text(errors='replace')[-18000:], flush=True)
    return code, folder
if __name__ == '__main__':
    code, _ = run(sys.argv[1], sys.argv[3:], int(sys.argv[2])); sys.exit(code)
