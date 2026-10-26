"""Snapshot bounded R1 inputs and verify old seals; never execute their code."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SEALS = [
    ("verification/swift-semantic-adapter-prerequisite/seal.json", ".", "d145cda8cdde0915493f5c75102ae0dc11adb577891b1b773322b5c4d0f32cba", 152),
    ("verification/swift-semantic-adapter-contract-review/review-1/seal.json", "verification/swift-semantic-adapter-contract-review/review-1", "d44b2edd19961ebeda7e197f549433e7a0d7f0630ce7d501e5465044340c6c02", 35),
    ("verification/swift-semantic-adapter-contract-review/preaccess/seal.json", "verification/swift-semantic-adapter-contract-review/preaccess", "7ae911b982f2bf96f596969c2c282bd5bbdd7302033a6d1404278f1df23d9ae9", 21),
]
INPUTS = [
    "AGENTS.md", "mixer-product-plan.md",
    "docs/swift-semantic-adapter-prerequisite.md",
    "verification/swift-semantic-adapter-prerequisite/contract.json",
    "docs/swift-semantic-adapter-contract-review.md",
    "verification/swift-semantic-adapter-contract-review/review-1/findings.json",
    "verification/swift-envelope-ci-pack/source/library/analyzer.rs",
    "verification/swift-envelope-ci-pack/source/library/envelope.rs",
    "verification/swift-envelope-ci-pack/manifest.json",
    "docs/swift-envelope-ci-acceptance.md",
] + [row[0] for row in SEALS]

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def check_old():
    results = []
    for relative, directory, expected, count in SEALS:
        raw = (ROOT / relative).read_bytes()
        if sha(raw) != expected:
            raise ValueError("Changed old seal: " + relative)
        seal = json.loads(raw)
        if len(seal["members"]) != count:
            raise ValueError("Old member count mismatch")
        total = 0
        for row in seal["members"]:
            member = Path(row["path"])
            if member.is_absolute() or ".." in member.parts:
                raise ValueError("Unbounded old member path")
            data = (ROOT / directory / member).read_bytes()
            total += len(data)
            if len(data) != row["bytes"] or sha(data) != row["sha256"]:
                raise ValueError("Changed old member: " + str(member))
        pair = (ROOT / relative).with_name("seal.sha256")
        if pair.read_text().split()[0] != expected:
            raise ValueError("Old seal pair differs")
        results.append({"path":relative,"member_base":directory,"sha256":expected,
                        "members":count,"bytes":total,"seal_pair_sha256":sha(pair.read_bytes())})
    return results

def main():
    target = BASE / "input-manifest.json"
    if target.exists():
        raise SystemExit("Refuse to overwrite input freeze")
    old = check_old()
    rows = []
    (BASE / "inputs").mkdir(exist_ok=True)
    for index, relative in enumerate(INPUTS):
        raw = (ROOT / relative).read_bytes()
        if len(raw) > 1_048_576:
            raise ValueError("Declared input exceeds 1MiB")
        snapshot = "inputs/%02d-%s" % (index,Path(relative).name)
        with (BASE / snapshot).open("xb") as output:
            output.write(raw)
        rows.append({"path":relative,"snapshot":snapshot,"bytes":len(raw),"sha256":sha(raw)})
    revision = subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,
                              check=True,timeout=15).stdout.decode().strip()
    tree = "".join("%s\t%d\t%s\n"%(r["path"],r["bytes"],r["sha256"])
                   for r in sorted(rows,key=lambda r:r["path"]))
    result = {"schema":1,"argv":sys.argv,"cwd":str(ROOT),"python":sys.version,
              "context_revision":revision,"members":rows,"old_seals_before":old,
              "consulted_tree_sha256":sha(tree.encode()),
              "scope":"bounded source/custody only; no old source/model/harness imported or executed"}
    with target.open("x") as output:
        json.dump(result,output,indent=2,sort_keys=True);output.write("\n")
    print(json.dumps({"inputs":len(rows),"old_members_verified":sum(r["members"] for r in old),
                      "consulted_tree_sha256":result["consulted_tree_sha256"]}))

if __name__ == "__main__":
    main()
