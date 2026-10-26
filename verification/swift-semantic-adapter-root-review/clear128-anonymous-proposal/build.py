"""Freeze a source-only alternative for independent review; never execute it."""
import difflib
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
assert not (HERE / "seal.json").exists(), "proposal is immutable after sealing"
source = ROOT / "verification/swift-cache-state-implementation/correction-2/source/library/cache_state.rs"
before = source.read_text()
assert hashlib.sha256(source.read_bytes()).hexdigest() == "6f128e861478c4c871460115397976b39e6cd3a4807a8825b5b04959e1930a00"
old = """    let zero = [0u8; 8];
    for i in 0..256 {
        let at = i * 8;
        c[at..at + 8].copy_from_slice(&zero);
    }
"""
assert before.count(old) == 1
ranges = [(i * 128, (i + 1) * 128) for i in range(16)]
fragment = "".join(f"    c[{start}..{end}].copy_from_slice(&[0u8; 128]);\n" for start, end in ranges)
after = before.replace(old, fragment)
anchor = "    c[888..896].copy_from_slice(&b[7729816..7729824]);"
assert before[before.index(anchor):] == after[after.index(anchor):]
covered = [byte for start, end in ranges for byte in range(start, end)]
assert covered == list(range(2048))
(HERE / "cache_state.rs").write_text(after)
(HERE / "fragment.rs.txt").write_text(fragment)
(HERE / "proposal.diff").write_text("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile="frozen-correction2/cache_state.rs", tofile="unselected-anonymous-clear128/cache_state.rs")))
receipt = {
    "schema": 1,
    "at": datetime.now(timezone.utc).isoformat(),
    "command": [sys.executable, "-B", str(Path(__file__).resolve())],
    "python": sys.version,
    "source": str(source.relative_to(ROOT)),
    "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
    "proposed_sha256": hashlib.sha256(after.encode()).hexdigest(),
    "status": "source-only unselected alternative awaiting independent review",
    "ranges": ranges,
    "byte_coverage": "all2048 bytes exactly once; no other product-source changes",
    "restore_fault_suffix_identical": True,
    "proposed_payload_accounting": "16 anonymous128-byte initializer places plus16 fixed destination copies =32 groups; complete scalar/helper bound unproved",
    "lifetime_hypothesis": "Each &[0u8;128] borrows one anonymous128-byte temporary directly, with no named128-byte local or by-value array parameter. Expression-statement temporary scope ends before the next statement. Promotion/elision is not used as credit. Independent review must validate place count and full phase coexistence.",
    "role_hypothesis": "One128-byte temporary plus live Paid24 totals152 within wire256 only if all other simultaneous role members are explicitly reconciled. This is not whole-role acceptance.",
    "official_references": [
        "https://doc.rust-lang.org/reference/expressions/operator-expr.html#borrow-operators",
        "https://doc.rust-lang.org/reference/destructors.html#temporary-scopes"
    ],
    "product_compiler_runtime_tests": 0,
    "implementation_selected": False,
    "full_work_or_lifetime_accepted": False,
    "caps_changed": False
}
(HERE / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
members = []
for path in sorted(HERE.iterdir()):
    assert path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    members.append({"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
seal = {"schema": 1, "at": receipt["at"], "status": receipt["status"], "members": members, "member_count": len(members), "member_bytes": sum(m["bytes"] for m in members)}
(HERE / "seal.json").write_text(json.dumps(seal, indent=2) + "\n")
print(json.dumps({"seal": str((HERE / "seal.json").relative_to(ROOT)), "sha256": hashlib.sha256((HERE / "seal.json").read_bytes()).hexdigest(), "members": seal["member_count"], "bytes": seal["member_bytes"], "proposed_source_sha256": receipt["proposed_sha256"]}))
