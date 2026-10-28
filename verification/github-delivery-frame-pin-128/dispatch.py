"""Exactly one dispatch after exact local/remote/workflow binding; never retry."""
import hashlib
import json
import re
from owned import Commands, OUT, ROOT, now, row, save

workflow_name = "swift-frame-pin-admission.yml"
workflow_path = ".github/workflows/" + workflow_name
assert not (OUT / "dispatch-once.json").exists(), "dispatch already reserved; never retry"
receipt = json.loads((OUT / "receipt.json").read_bytes())
selection = json.loads((OUT / "selection.json").read_bytes())
head = receipt["commit"]
commands = Commands(180)
assert receipt["pushed"] and not receipt["force"] and receipt["allNewCommandsReapedAndOwnedGroupsAbsent"]
assert commands.run("dispatch-local-head", ["git", "rev-parse", "HEAD"]).decode().strip() == head
assert commands.run("dispatch-remote-head", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
assert commands.run("dispatch-local-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == receipt["tree"]
assert row(ROOT / workflow_path) == selection["workflow"]
remote = json.loads(commands.run("dispatch-workflow-content", ["gh", "api", "repos/snowdamiz/mixer/contents/" + workflow_path + "?ref=" + head]))
import base64
assert remote["encoding"] == "base64" and base64.b64decode(remote["content"]) == (ROOT / workflow_path).read_bytes()
workflow = json.loads(commands.run("dispatch-workflow-state", ["gh", "api", "repos/snowdamiz/mixer/actions/workflows/" + workflow_name]))
assert workflow["state"] == "active" and workflow["path"] == workflow_path
commands.run("gh-version", ["gh", "--version"])
# Reserve before the mutating call, including an ambiguous/error outcome. Never resubmit.
save("dispatch-once.json", {"schema": 1, "at": now(), "head": head, "tree": receipt["tree"],
     "workflow": workflow_name, "workflowSHA256": selection["workflow"]["sha256"], "profile": "paired-128-v1",
     "dispatchesAuthorized": 1, "dispatchReservationConsumed": True, "retryOrResumeSelected": False,
     "maxFullAttempts": 2, "maxCommands": 11, "aggregateSeconds": 2700})
output = commands.run("dispatch", ["gh", "workflow", "run", workflow_name, "--ref", "main", "--repo", "snowdamiz/mixer", "-f", "profile=paired-128-v1"], cap=45)
match = re.search(rb"https://github\.com/snowdamiz/mixer/actions/runs/(\d+)", output)
run = None
if match:
    run = json.loads(commands.run("dispatch-run-binding", ["gh", "api", "repos/snowdamiz/mixer/actions/runs/" + match[1].decode()]))
    assert run["head_sha"] == head and run["event"] == "workflow_dispatch" and run["run_attempt"] == 1
    assert run["workflow_id"] == workflow["id"] and run["path"] == workflow_path
save("dispatch-receipt.json", {"schema": 1, "at": now(), "head": head, "tree": receipt["tree"],
     "profile": "paired-128-v1", "dispatchCallsMade": 1, "dispatchCommandSucceeded": True,
     "runId": int(match[1]) if match else None, "runURL": match[0].decode() if match else None,
     "resultingRunHeadBound": run is not None,
     "runHead": run["head_sha"] if run else None, "runAttempt": run["run_attempt"] if run else None,
     "runStatus": run["status"] if run else None,
     "runIndexMayLag": True, "actualRuntimeResult": "pending root independent review",
     "allNewCommands": commands.records, "allNewCommandsReapedAndOwnedGroupsAbsent": True,
     "GA_accepted": False})
print(output.decode().strip())
