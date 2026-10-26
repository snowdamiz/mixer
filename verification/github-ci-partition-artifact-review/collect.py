#!/usr/bin/env python3
"""Read-only GitHub evidence collector. Captured bytes are never rendered."""
import concurrent.futures
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SHA = "a24011487bfc368512fa52125241d9c46e7cdd3f"
RUN = 40354171285


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def capture(name, argv):
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=REPO, capture_output=True, check=False)
    for ext, payload in (("stdout", result.stdout), ("stderr", result.stderr)):
        (ROOT / f"{name}.{ext}").write_bytes(payload)
    receipt = {
        "started_utc": started,
        "completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "argv": argv,
        "cwd": str(REPO),
        "exit_code": result.returncode,
        "stdout": {"bytes": len(result.stdout), "sha256": hashlib.sha256(result.stdout).hexdigest()},
        "stderr": {"bytes": len(result.stderr), "sha256": hashlib.sha256(result.stderr).hexdigest()},
    }
    write_json(ROOT / f"{name}.command.json", receipt)
    if result.returncode:
        raise RuntimeError(f"{name} failed; inspect retained bytes safely")
    return result.stdout


def initial():
    commands = {
        "artifact-metadata": ["gh", "api", f"repos/snowdamiz/mixer/actions/runs/{RUN}/artifacts?per_page=100"],
        "workflow-source": ["git", "show", f"{SHA}:.github/workflows/verify.yml"],
        "source-tree": ["git", "rev-parse", f"{SHA}^{{tree}}"],
        "gh-version": ["gh", "--version"],
        "git-version": ["git", "--version"],
        "python-version": [sys.executable, "--version"],
    }
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda item: (item[0], capture(*item)), commands.items()))
    artifacts = json.loads(dict(results)["artifact-metadata"])["artifacts"]
    summary = [{key: a.get(key) for key in ("id", "name", "size_in_bytes", "digest", "expired", "created_at", "updated_at", "workflow_run")} for a in artifacts]
    write_json(ROOT / "artifact-list.json", summary)
    print(json.dumps(summary, indent=2))


def download():
    artifacts = json.loads((ROOT / "artifact-metadata.stdout").read_bytes())["artifacts"]
    selected = [a for a in artifacts if a["name"] in {
        f"swift-core-toolchain-host-{SHA}", f"android-owner-host-{SHA}", f"android-binding-host-{SHA}"
    }]
    for artifact in selected:
        name = artifact["name"].removesuffix("-" + SHA)
        path = ROOT / (name + ".zip")
        if path.exists():
            continue
        payload = capture(name, ["gh", "api", f"repos/snowdamiz/mixer/actions/artifacts/{artifact['id']}/zip"])
        path.write_bytes(payload)
        (ROOT / (name + ".stdout")).unlink()
        print(json.dumps({"artifact": name, "id": artifact["id"], "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}))


if __name__ == "__main__":
    {"initial": initial, "download": download}[sys.argv[1]]()
