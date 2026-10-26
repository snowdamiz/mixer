"""Finite owned command/evidence runner; 60 second ordinary bound; one explicitly selected cold context permits180."""
import datetime, hashlib, json, os, signal, subprocess, sys, time, shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
label=sys.argv[1]; command=sys.argv[2:]
budget=60;execution_timeout=56;amendment=None
if command and command[0]=='--cold180':
    command=command[1:]
    assert label=='cli-release-original-context-final'
    amendment_path=HERE.parents[1]/'verification/android-editor-boundary-root-review/integration-cold-build-command-budget-amendment.md'
    amendment=hashlib.sha256(amendment_path.read_bytes()).hexdigest()
    assert amendment=='8cef0df4db8ddaf9b9fefdc5b5a1b29298b3107f0243cb22867cd335e822f266'
    budget=180;execution_timeout=176
assert label and '/' not in label and command
out=HERE/'evidence'; out.mkdir(exist_ok=True)
assert not (out/(label+'.json')).exists(), 'Use a fresh command label'
exe=shutil.which(command[0]) or command[0]
exe=Path(exe)
if not exe.is_absolute(): exe=HERE/'source'/exe
exe=exe.resolve()
start=time.monotonic(); stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
process=subprocess.Popen(command,cwd=HERE/'source',stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
timed_out=False
try: output,_=process.communicate(timeout=execution_timeout)
except subprocess.TimeoutExpired:
    timed_out=True; os.killpg(process.pid,signal.SIGTERM)
    try: output,_=process.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL); output,_=process.communicate(timeout=2)
(out/(label+'.log')).write_bytes(output)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
for base, dirs, files in os.walk(HERE/'source'):
    dirs[:]=sorted(d for d in dirs if not d.startswith('.build') and d not in ('.swiftpm','__pycache__','.git'))
    for name in sorted(files):
        p=Path(base)/name
        if p.is_file() and not p.is_symlink(): records.append((str(p.relative_to(HERE/'source')),p.stat().st_size,sha(p)))
records.sort()
digest=hashlib.sha256(''.join(rel+'\0'+h+'\n' for rel,size,h in records).encode()).hexdigest()
row={'schema':1,'label':label,'at':stamp,'command':command,'cwd':str(HERE/'source'),'deadline_seconds':budget,'execution_timeout_seconds':execution_timeout,'cold_build_budget_amendment_sha256':amendment,'returncode':process.returncode,'timed_out':timed_out,'elapsed_seconds':time.monotonic()-start,'executable':str(exe),'executable_sha256':sha(exe),'source_tree_sha256':digest,'source_members':len(records),'output_sha256':sha(out/(label+'.log')),'output_bytes':len(output),'owned_child_reaped':process.poll() is not None}
(out/(label+'.json')).write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row)); print(output.decode(errors='replace')[-6000:])
sys.exit(124 if timed_out else process.returncode)
