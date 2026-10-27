"""Owned adaptation of released host runner, with independently selected replay.

Frozen author files are read only. No frozen runner/finalizer executes in place.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = ROOT / "verification/swift-selected-profile-adoption"
REPLAY = HERE / "replay"
SEAL = "83a7c57bc5f208b06a42384f14b4056040604ef01685a9dfbe8bbe32b832a7ad"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def load(p):
    return json.loads(p.read_bytes())


def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")


def custody():
    assert sha((CANDIDATE / "seal.json").read_bytes()) == SEAL
    seal = load(CANDIDATE / "seal.json")
    members = seal["members"]
    actual = set()
    for p in CANDIDATE.rglob("*"):
        assert not p.is_symlink(), str(p)
        if p.is_file():
            actual.add(str(p.relative_to(CANDIDATE)))
    assert actual == {m["path"] for m in members} | {"seal.json"}
    for m in members:
        b = (CANDIDATE / m["path"]).read_bytes()
        assert len(b) == m["bytes"] and sha(b) == m["sha256"], m["path"]
    return {"seal_sha256": SEAL, "members": len(members),
            "member_bytes": sum(m["bytes"] for m in members),
            "all_bytes_and_exact_closed_file_set_verified": True}


def prepare():
    assert not REPLAY.exists()
    verified = custody()
    REPLAY.mkdir()
    source = load(CANDIDATE / "source-manifest.json")
    for m in source["members"]:
        dst = REPLAY / "source/vm" / m["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CANDIDATE / "source/vm" / m["path"], dst)
    shutil.copytree(CANDIDATE / "host", REPLAY / "host")
    names = ["evidence.py", "selection.json", "prepare_inputs.py", "implement_selected.py",
             "extend_roster.py", "migrate_literals.py", "contracts.py", "public_contracts.py",
             "CONTRACT-PROPOSAL.md", "appended-layout-types.json"]
    for name in names:
        shutil.copyfile(CANDIDATE / name, REPLAY / name)
    old = (REPLAY / "evidence.py").read_text()
    new = old.replace("HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1];SOURCE=HERE/'source/vm'",
                      "HERE=Path(__file__).resolve().parent;REPO=Path(" + repr(str(ROOT)) + ");SOURCE=HERE/'source/vm'")
    new = new.replace("revision,_,_=run('revision',['git','rev-parse','HEAD'])",
                      "revision='root-released-source-tree22b6e945a062b3465156bb9995bce610bd712fa9d3e283e176316d75104bb442'")
    assert old != new and "['git','rev-parse','HEAD']" not in new
    (REPLAY / "evidence.py").write_text(new)
    write(HERE / "replay-adaptation.json", {
        "schema": 1, "candidate_custody": verified,
        "baseline_source": source,
        "frozen_runner_sha256": sha(old.encode()), "owned_runner_sha256": sha(new.encode()),
        "changes": ["Set REPO to actual repository because owned replay is nested one level deeper",
                    "Replace read-only Git revision command with root-released immutable source context; no Git command used"],
        "frozen_runner_executed_in_place": False,
        "all_144_distribution_and_11_host_support_bytes_copied_unchanged": True,
    })
    print("Prepared exact source144 and support11; adapted owned runner", flush=True)


def module():
    spec = importlib.util.spec_from_file_location("owned_adoption_evidence", REPLAY / "evidence.py")
    e = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(e)
    return e


def behavior(e, mode, include_control=True):
    initial = []
    selected = []
    loader = []
    matrix = load(CANDIDATE / "final-required-command-matrix.json")
    for label, rel in matrix["by_label"].items():
        r = load(CANDIDATE / rel)
        a = r["argv"]
        if "--exact" not in a or not a[0].endswith("unit-" + mode):
            continue
        if "initial_profile_v1::tests::" in a[2]:
            initial.append(a[2].split("::")[-1])
        elif label.startswith(mode + "-adopt-"):
            selected.append(label.removeprefix(mode + "-adopt-"))
        elif a[2] == e.PREFIX + "actual_selected_loader_child":
            loader.append(label.removeprefix(mode + "-"))
    assert len(initial) == 17 and len(selected) == 15 and len(loader) == 37
    if include_control:
        e.suite(mode, "experimental_swift_reactor::control::tests::")
    e.suite(mode, "experimental_swift_reactor::cache_tests::")
    e.suite(mode, "experimental_swift_reactor::execution_tests::")
    e.initial(mode, initial)
    e.selected(mode, selected)
    e.selected(mode, loader, ordinary=True)
    directory = e.WORK / ("independent-helper-" + mode)
    directory.mkdir()
    env = e.cleanenv() | {"MIXER_LOADER_HELPER_DIR": str(directory)}
    e.run(mode + "-loader-helpers", [e.WORK / ("unit-" + mode), e.PREFIX,
          "--skip", "actual_selected_loader_child", "--nocapture", "--test-threads=1"], env)
    shutil.rmtree(directory)


def main():
    stage = sys.argv[1]
    if stage == "prepare":
        prepare()
        return
    e = module()
    mode = sys.argv[2] if len(sys.argv) > 2 else "debug"
    if stage == "compile":
        e.compile(mode)
    elif stage == "behavior":
        behavior(e, mode)
    elif stage == "behavior-rest":
        behavior(e, mode, include_control=False)
    elif stage == "layout":
        e.measure(mode)
        e.compile(mode, host=True)
        e.measure(mode, host=True)
        e.host_methods(mode, list(map(str, range(1, 9))))
        e.ordinary(mode)
    elif stage == "custody":
        write(HERE / "candidate-post-review-custody.json", custody())
    else:
        raise AssertionError(stage)


if __name__ == "__main__":
    main()
