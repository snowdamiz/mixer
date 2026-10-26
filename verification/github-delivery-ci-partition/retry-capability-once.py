"""One selected retry of the zero-step runner-capacity cancellation."""
import datetime, hashlib, json, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent / "capability-targeted-retry"
OUT.mkdir(exist_ok=False)

def command(name, argv):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    for suffix, data in (("stdout", result.stdout), ("stderr", result.stderr)):
        (OUT / f"{name}.{suffix}").write_bytes(data)
    receipt = {"argv": argv, "started": started, "completed": datetime.datetime.now(datetime.timezone.utc).isoformat(), "exit_code": result.returncode,
               "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(), "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}
    (OUT / f"{name}.command.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if result.returncode:
        raise RuntimeError(f"{name} exited {result.returncode}; retained output")
    return result.stdout

command("gh-version", ["gh", "--version"])
snapshot = json.loads(command("before", ["gh", "run", "view", "40354171285", "--repo", "snowdamiz/mixer", "--json", "status,conclusion,jobs,headSha,updatedAt"]))
if snapshot["headSha"] != "a24011487bfc368512fa52125241d9c46e7cdd3f" or snapshot["status"] != "completed":
    raise RuntimeError("Unexpected run identity or nonterminal status")
jobs = {job["name"]: job for job in snapshot["jobs"]}
if set(jobs) != {"swift", "swift-capability-native", "vm", "services", "android-owner-host"}:
    raise RuntimeError("Unexpected job set")
if any(jobs[name]["conclusion"] != "success" for name in jobs if name != "swift-capability-native"):
    raise RuntimeError("Other jobs did not all succeed")
job = jobs["swift-capability-native"]
if job["databaseId"] != 121682022575 or job["conclusion"] != "cancelled" or job["steps"]:
    raise RuntimeError("Unexpected cancelled job or executed steps")
command("rerun", ["gh", "run", "rerun", "40354171285", "--job", "121682022575", "--repo", "snowdamiz/mixer"])
receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "run_id": 40354171285, "retried_job_id": 121682022575, "source_revision": snapshot["headSha"], "targeted_retries_executed": 1, "maximum_selected_retries": 1, "other_jobs_before_retry": "all four successful", "reason": "First capability job executed zero steps because no hosted runner was acquired", "acceptance": "pending retry terminal outcome and artifact review"}
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
