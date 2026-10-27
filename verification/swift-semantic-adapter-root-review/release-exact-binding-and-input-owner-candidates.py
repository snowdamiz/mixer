"""One-shot root custody release; no semantic acceptance or product execution."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    specifications = [
        ("swift-guarded-snapshot-string-exact-binding-correction",
         "4eb0437b5ed1f7ec056340ffac08a0221cfd5f6f216a9d3aebb6fd4d25cc5f4b",
         895, 70066404, "guarded-snapshot-string-exact-binding-frozen-release.json",
         "690755b7bfacf1b1ee03b4c60319a4be65fdd72ff20e4897a080bfebfd480185"),
        ("swift-guarded-snapshot-prepaid-input-owner-contract",
         "9c73d3405370a71ad447136ab7a4e56c2d45dbf4fd4627c319a8626f8a53033e",
         36, 448460, "guarded-snapshot-prepaid-input-owner-frozen-release.json",
         "acce2edaeb41d2e032cd9417897f828caa1c713721e162d2f455663600076e3d"),
    ]
    assert all(not (OUT / item[4]).exists() for item in specifications), "one-shot release already exists"
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=10, text=True).strip()
    tool = {"argv": sys.argv, "python": sys.version,
            "executable": sys.executable,
            "executable_sha256": sha(Path(sys.executable).resolve().read_bytes()),
            "script_sha256": sha(Path(__file__).read_bytes())}
    ready = []
    for name, expected, count, size, output, source_tree in specifications:
        packet = ROOT / "verification" / name
        raw = (packet / "seal.json").read_bytes()
        assert sha(raw) == expected, name
        seal = json.loads(raw)
        members = seal["members"]
        names = [m["path"] for m in members]
        assert len(names) == len(set(names)) == count == seal["member_count"]
        assert sum(m["bytes"] for m in members) == size
        assert seal.get("bytes", seal.get("member_bytes")) == size
        assert all(not p.is_symlink() for p in packet.rglob("*"))
        actual = {str(p.relative_to(packet)) for p in packet.rglob("*") if p.is_file()}
        assert actual == set(names) | {"seal.json"}, name
        for member in members:
            relative = Path(member["path"])
            assert not relative.is_absolute() and ".." not in relative.parts
            data = (packet / relative).read_bytes()
            assert len(data) == member["bytes"] and sha(data) == member["sha256"], member["path"]
        receipt = {"schema": 1, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   "status": "root-rehashed-frozen-candidate-released-for-fresh-independent-review",
                   "path": str(packet.relative_to(ROOT)), "seal_sha256": expected,
                   "members": count, "bytes": size, "source_tree_sha256": source_tree,
                   "root_HEAD": head, "complete_membership_and_all_digests_match": True,
                   "all_files_read_only": all(p.stat().st_mode & 0o222 == 0 for p in packet.rglob("*") if p.is_file()),
                   "tool": tool, "scope": "pure host custody only; candidate claims are not independently accepted",
                   "fresh_independent_review_required": True, "accepted": False,
                   "L_str_or_root_policy_or_funding_selected": False,
                   "compiler_or_product_or_native_execution": False,
                   "operational_grant_or_OTA_or_GA": False}
        ready.append((OUT / output, receipt))
    for target, receipt in ready:
        with target.open("x") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
        print(json.dumps({"path": str(target.relative_to(ROOT)), "sha256": sha(target.read_bytes()),
                          "members": receipt["members"], "bytes": receipt["bytes"]}))


if __name__ == "__main__":
    main()
