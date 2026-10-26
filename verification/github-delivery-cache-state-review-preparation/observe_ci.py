"""Read the authorized source-contract CI run and retain exact observations."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
JOBS = {
    "preparation": (40290654299, "verification/github-delivery-cache-state-review-preparation", "5c1cf075be26b7a71297552723861ef893e69e7d"),
}
for label in sys.argv[1:] or JOBS:
    run_id, directory, commit = JOBS[label]
    root = ROOT / directory
    suffix = 1
    while (root / ("ci-observation-" + str(suffix))).exists():
        suffix += 1
    out = root / ("ci-observation-" + str(suffix))
    out.mkdir()
    argv = ["gh", "run", "view", str(run_id), "--repo", "snowdamiz/mixer", "--json", "status,conclusion,headSha,jobs,url,updatedAt"]
    result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
    (out / "stdout.json").write_bytes(result.stdout)
    (out / "stderr").write_bytes(result.stderr)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (out / "command.json").write_text(json.dumps({"argv": argv, "exit": result.returncode, "at": now,
        "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(), "stderr_sha256": hashlib.sha256(result.stderr).hexdigest()}, indent=2) + "\n")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["headSha"] == commit
    complete = data["status"] == "completed"
    all_passed = complete and data["conclusion"] == "success" and len(data["jobs"]) == 3 and all(
        j["status"] == "completed" and j["conclusion"] == "success" and j["steps"] and all(
            s["status"] == "completed" and s["conclusion"] == "success" for s in j["steps"])
        for j in data["jobs"])
    receipt_path = root / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    receipt.update(status="pushed-ci-passed" if all_passed else "pushed-ci-" + (data["conclusion"] if complete else data["status"].replace("_", "-")),
        ci_status=data["status"], ci_conclusion=data["conclusion"], last_observed_at=now,
        latest_observation=(out / "stdout.json").relative_to(ROOT).as_posix(), all_jobs_and_steps_passed=all_passed,
        observed_jobs=len(data["jobs"]), observed_steps=sum(len(j["steps"]) for j in data["jobs"]))
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"label": label, "status": receipt["status"], "all_passed": all_passed,
        "jobs": [{"name": j["name"], "status": j["status"], "conclusion": j["conclusion"],
                  "running": [s["name"] for s in j["steps"] if s["status"] == "in_progress"],
                  "failed": [s["name"] for s in j["steps"] if s["conclusion"] in ("failure", "timed_out", "cancelled")]} for j in data["jobs"]]}))
