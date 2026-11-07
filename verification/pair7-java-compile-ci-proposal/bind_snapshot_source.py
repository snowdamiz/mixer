"""Proposal-only source binder. No subject import or child command is used."""
import sys
sys.dont_write_bytecode = True
if not (sys.flags.isolated == 1 and sys.flags.no_site == 1):
    raise RuntimeError("Run with -I -B -S")
def source_guard(event, args):
    if event.startswith(("subprocess", "socket", "ctypes")) or event in (
        "os.system", "os.posix_spawn", "os.posix_spawnp", "os.fork", "os.forkpty",
        "os.kill", "os.killpg", "os.exec", "pty.spawn"):
        raise RuntimeError("Data-only source binder denied " + event)
    if event == "import" and args[0].split(".")[0] not in sys.stdlib_module_names:
        raise RuntimeError("Non-stdlib import denied " + args[0])
sys.addaudithook(source_guard)
import hashlib
import json
import os
from pathlib import Path
import stat

def need(value, message):
    if not value:
        raise RuntimeError(message)
def info(path):
    data = path.read_bytes()
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
def regular(path, root):
    need(path.is_relative_to(root), "Path escapes checkout")
    cursor = path
    while cursor != root:
        kind = cursor.lstat().st_mode
        need(not stat.S_ISLNK(kind), "Symlink in source path")
        cursor = cursor.parent
    need(stat.S_ISREG(path.lstat().st_mode), "Ordinary file required")
    return path
def save(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")

def main():
    need(len(sys.argv) == 2 and sys.argv[1] in ("stage", "post"), "stage or post required")
    root = Path(os.environ["GITHUB_WORKSPACE"])
    need(root.is_absolute() and root.resolve() == root, "Canonical checkout required")
    need(os.environ.get("GITHUB_REPOSITORY") == "snowdamiz/mixer", "Exact repository required")
    need(os.environ.get("GITHUB_EVENT_NAME") in ("push", "pull_request"), "Ordinary CI required")
    need(os.environ.get("GITHUB_RUN_ATTEMPT") == "1", "No retry allowance")
    run = os.environ["GITHUB_RUN_ID"]
    need(run.isascii() and run.isdecimal(), "Run id required")
    packet = root / "verification/pair7-java-compile-ci-proposal"
    manifest_path = regular(packet / "snapshot-source-manifest.json", root)
    manifest = json.loads(manifest_path.read_bytes())
    rows = manifest["members"]
    need(len(rows) == manifest["count"] == 141 and sum(r["bytes"] for r in rows) == manifest["bytes"], "Manifest totals changed")
    expected = set()
    for row in rows:
        name = row["path"]
        need(name not in expected and not Path(name).is_absolute() and ".." not in Path(name).parts, "Invalid source path")
        expected.add(name)
        need(info(regular(root / name, root)) == {k:row[k] for k in ("bytes", "sha256")}, "Source changed: " + name)
    overlay = manifest["overlay"]
    target = root / overlay["target"]
    source = regular(root / overlay["source"], root)
    need(info(source)["sha256"] == overlay["sha256"], "Producer source changed")
    for folder in manifest["closed_directories"]:
        observed = set()
        for path in (root / folder).rglob("*"):
            need(not path.is_symlink(), "Symlink in closed source directory")
            if path.is_file(): observed.add(path.relative_to(root).as_posix())
        wanted = {name for name in expected if name.startswith(folder + "/")}
        if sys.argv[1] == "post" and target.is_relative_to(root / folder):
            wanted.add(overlay["target"])
        need(observed == wanted, "Closed source membership changed: " + folder)
    temp = Path(os.environ["RUNNER_TEMP"])
    need(temp.is_absolute() and temp.resolve() == temp, "Canonical runner temp required")
    evidence = temp / ("pair7-java-source-" + run + "-1")
    if sys.argv[1] == "stage":
        evidence.mkdir(exist_ok=False)
        need(not target.exists() and not target.is_symlink(), "Existing test target refused")
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
    else:
        need(info(regular(target, root))["sha256"] == overlay["sha256"], "Staged producer changed")
    save(evidence / (sys.argv[1] + ".json"), {
        "schema":1, "status":"source-bound-only", "mode":sys.argv[1],
        "source_head":os.environ["GITHUB_SHA"], "run_id":run, "run_attempt":1,
        "python":sys.version, "argv":sys.argv, "binder":info(Path(__file__)),
        "manifest":info(manifest_path), "source_members":rows,
        "producer":info(source), "overlay":overlay,
        "product_compiler_or_runtime_started_by_binder":False,
        "cleanup":"No child started. CI-only staged test and source observations retained."
    })
if __name__ == "__main__":
    main()
