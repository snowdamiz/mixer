"""Capture one bounded remote CI observation for the committed source export."""
import datetime
import json
import subprocess
from pathlib import Path

OUT = Path(__file__).resolve().parent
receipt = json.loads((OUT / "receipt.json").read_text())
run_id = receipt["ci"][0]["databaseId"]
number = 1 + max((int(x.name.rsplit("-", 1)[1]) for x in OUT.glob("ci-observation-*")), default=0)
folder = OUT / f"ci-observation-{number}"
folder.mkdir()
argv = ["gh", "run", "view", str(run_id), "--repo", "snowdamiz/mixer", "--json",
        "databaseId,workflowName,status,conclusion,url,headSha,jobs"]
result = subprocess.run(argv, capture_output=True, timeout=45)
(folder / "stdout.json").write_bytes(result.stdout)
(folder / "stderr").write_bytes(result.stderr)
(folder / "command.json").write_text(json.dumps({
    "argv": argv, "exit": result.returncode,
    "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "tool_version": "../gh-version.stdout"
}, indent=2) + "\n")
assert result.returncode == 0
observed = json.loads(result.stdout)
assert observed["headSha"] == receipt["commit"]
all_passed = (
    observed["status"] == "completed" and observed["conclusion"] == "success"
    and len(observed["jobs"]) == 3
    and all(job["conclusion"] == "success" and job["steps"]
            and all(step["conclusion"] == "success" for step in job["steps"])
            for job in observed["jobs"])
)
receipt["ci_last_observation"] = folder.name + "/stdout.json"
receipt["ci"] = [{k: v for k, v in observed.items() if k != "jobs"}]
receipt["all_jobs_and_steps_passed"] = all_passed
if all_passed:
    receipt["status"] = "pushed-ci-passed"
    receipt["pending"] = [x for x in receipt["pending"] if x != "Remote Engine CI"]
elif observed["status"] == "completed":
    receipt["status"] = "pushed-ci-terminal-review-required"
(OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"status": observed["status"], "conclusion": observed["conclusion"],
                  "all_jobs_and_steps_passed": all_passed,
                  "jobs": [{"name": job["name"], "status": job["status"],
                            "conclusion": job["conclusion"],
                            "passed_steps": sum(x["conclusion"] == "success" for x in job["steps"]),
                            "steps": len(job["steps"])} for job in observed["jobs"]]}))
