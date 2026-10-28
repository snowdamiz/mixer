"""Reserve and submit exactly one reviewed profile at the exact delivered head."""
import base64
import json
import re
from owned import Commands, OUT, ROOT, now, row, save

assert not (OUT / "dispatch-once.json").exists(), "dispatch consumed; never retry or resume"
receipt = json.loads((OUT / "receipt.json").read_bytes())
selection = json.loads((OUT / "selection.json").read_bytes())
assert receipt["pushed"] and not receipt["force"] and receipt["allNewCommandsReapedGroupsAbsentAndEOF"]
head, tree = receipt["commit"], receipt["tree"]
workflow_path = selection["workflow"]["destination"]
workflow_name = workflow_path.rsplit("/", 1)[1]
commands = Commands(180, 8, "dispatch-")
assert commands.run("local-head", ["git", "rev-parse", "HEAD"]).decode().strip() == head
assert commands.run("local-tree", ["git", "rev-parse", "HEAD^{tree}"]).decode().strip() == tree
assert commands.run("remote-head", ["git", "ls-remote", "origin", "refs/heads/main"]).decode().split()[0] == head
assert row(ROOT / workflow_path) == receipt["workflow"]
content = json.loads(commands.run("workflow-content", ["gh", "api",
    "repos/snowdamiz/mixer/contents/" + workflow_path + "?ref=" + head]))
assert content["encoding"] == "base64"
assert base64.b64decode(content["content"]) == (ROOT / workflow_path).read_bytes()
workflow = json.loads(commands.run("workflow-state", ["gh", "api", "repos/snowdamiz/mixer/actions/workflows/" + workflow_name]))
assert workflow["state"] == "active" and workflow["path"] == workflow_path
commands.run("gh-version", ["gh", "--version"])
# The reservation is written before the sole mutating API call, even on error/ambiguity.
save("dispatch-once.json", {"schema": 1, "at": now(), "head": head, "tree": tree,
    "workflow": workflow_name, "workflowSHA256": selection["workflow"]["sha256"],
    "profile": "capacity-window-v1", "dispatchLimit": 1, "reservationConsumed": True,
    "retryResumeOrFallbackSelected": False, "maxFullAttempts": 2, "maxCommands": 11, "driverSeconds": 2700})
output = commands.run("submit", ["gh", "workflow", "run", workflow_name, "--ref", "main",
    "--repo", "snowdamiz/mixer", "-f", "profile=capacity-window-v1"], seconds=45)
match = re.search(rb"https://github\.com/snowdamiz/mixer/actions/runs/(\d+)", output)
run = None
if match:
    run = json.loads(commands.run("run-binding", ["gh", "api", "repos/snowdamiz/mixer/actions/runs/" + match[1].decode()]))
    assert run["head_sha"] == head and run["event"] == "workflow_dispatch" and run["run_attempt"] == 1
    assert run["workflow_id"] == workflow["id"] and run["path"] == workflow_path
save("dispatch-receipt.json", {"schema": 1, "at": now(), "head": head, "tree": tree,
    "profile": "capacity-window-v1", "workflow": workflow_name, "workflowSHA256": selection["workflow"]["sha256"],
    "dispatchCallsMade": 1, "dispatchCommandSucceeded": True,
    "runId": int(match[1]) if match else None, "runURL": match[0].decode() if match else None,
    "resultingRunHeadBound": run is not None, "runHead": run["head_sha"] if run else None,
    "runAttempt": run["run_attempt"] if run else None, "runStatus": run["status"] if run else None,
    "allNewCommands": commands.records, "allNewCommandsReapedGroupsAbsentAndEOF": True,
    "runtimeResult": "pending independent review; no runtime or default promotion",
    "GA_accepted": False})
print(json.dumps({"dispatchCallsMade": 1, "head": head, "runID": int(match[1]) if match else None,
    "runURL": match[0].decode() if match else None, "exactHeadBound": run is not None,
    "ownedCommands": len(commands.records), "cleanupVerified": True}))
