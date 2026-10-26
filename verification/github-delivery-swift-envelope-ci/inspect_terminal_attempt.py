"""Retain terminal metadata for the first exact delivered Swift CI attempt."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "terminal-attempt-1"
OUT.mkdir(exist_ok=False)

def capture(name, argv):
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (OUT / (name + ".stdout")).write_bytes(result.stdout)
    (OUT / (name + ".stderr")).write_bytes(result.stderr)
    (OUT / (name + ".command.json")).write_text(json.dumps({
        "argv": argv, "exit": result.returncode,
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
    }, indent=2) + "\n")
    return result

version = capture("gh-version", ["gh", "--version"])
run = capture("run", ["gh", "api", "repos/snowdamiz/mixer/actions/runs/40273904826"])
assert run.returncode == 0
run_data = json.loads(run.stdout)
assert run_data["head_sha"] == "0b8e3fd8bdd86902f7d9d28e0cba01bcdbb5ce1c"
assert run_data["status"] == "completed" and run_data["run_attempt"] == 1
job = capture("job", ["gh", "api", "repos/snowdamiz/mixer/actions/jobs/121412447113"])
assert job.returncode == 0
job_data = json.loads(job.stdout)
assert job_data["status"] == "completed" and job_data["conclusion"] == "cancelled"
check_id = job_data["check_run_url"].rsplit("/", 1)[1]
assert check_id.isdecimal()
annotations = capture("annotations", ["gh", "api", "repos/snowdamiz/mixer/check-runs/" + check_id + "/annotations"])
logs = capture("log", ["gh", "run", "view", "40273904826", "--repo", "snowdamiz/mixer", "--attempt", "1", "--job", "121412447113", "--log"])
receipt_path = OUT.parent / "receipt.json"
receipt = json.loads(receipt_path.read_bytes())
receipt["attempt_1_terminal"] = {
    "status": job_data["status"], "conclusion": job_data["conclusion"],
    "job_database_id": job_data["id"], "started_at": job_data["started_at"],
    "completed_at": job_data["completed_at"],
    "last_active_step": "Run actions/checkout@v4",
    "inspection": OUT.relative_to(ROOT).as_posix(),
    "annotations": json.loads(annotations.stdout) if annotations.returncode == 0 else None,
    "log_exit": logs.returncode,
    "analyzer_or_compiler_started": False,
    "cause_limit": "Terminal annotations and logs are observations; no product test ran in this Swift attempt.",
}
receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"terminal": receipt["attempt_1_terminal"], "log_bytes": len(logs.stdout)}))
