"""One-shot isolated source preparation; never changes the frozen input packet."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[1]
INPUT = ROOT / "verification/swift-retained-profile-composition-stdio-correction"
EXPECTED = "01fde6f81a88a35fe734f66991324e2518967e2890a8485cf13a679fd01eeeb2"


def identity(path):
    value = path.read_bytes()
    return {"bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}


assert identity(INPUT / "seal.json")["sha256"] == EXPECTED
seal = json.loads((INPUT / "seal.json").read_text())
paths = set()
for member in seal["members"]:
    path = Path(member["path"])
    assert not path.is_absolute() and ".." not in path.parts and path.as_posix() not in paths
    assert not (INPUT / path).is_symlink()
    assert identity(INPUT / path) == {"bytes": member["bytes"], "sha256": member["sha256"]}
    paths.add(path.as_posix())
assert len(paths) == 659
assert (INPUT / "seal.sha256").read_bytes() == (EXPECTED + "  seal.json\n").encode()
assert {p.relative_to(INPUT).as_posix() for p in INPUT.rglob("*") if p.is_file()} == paths | {"seal.json", "seal.sha256"}
copies = []
for variant in ("old", "new"):
    target = D / variant / "replay/corrected/replay"
    target.mkdir(parents=True)
    for name in ("prototype.py", "schema.py", "consumer.py", "test_preparation.py"):
        source = INPUT / "new/replay/corrected/replay" / name
        shutil.copyfile(source, target / name)
        copies.append({"source": str(source.relative_to(ROOT)), "target": str((target / name).relative_to(D)), **identity(source)})
shutil.copyfile(INPUT / "new/replay/fault_case.py", D / "new/replay/fault_case.py")
shutil.copyfile(INPUT / "stdio_case.py", D / "stdio_case.py")
source = D / "new/replay/corrected/replay/prototype.py"
old = source.read_text()
before = '            parts.append(part);remaining-=len(part)\n        raise Refusal("stdio-read-attempts","stdio-access")\n'
after = '            parts.append(part);remaining-=len(part)\n        if remaining==0:return b"".join(parts)\n        raise Refusal("stdio-read-attempts","stdio-access")\n'
assert old.count(before) == 1
new = old.replace(before, after)
source.write_text(new)
(D / "source.patch").write_text("".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile="old/prototype.py", tofile="new/prototype.py")))
(D / "input-custody.json").write_text(json.dumps({"schema": 1, "input": str(INPUT.relative_to(ROOT)), "seal_sha256": EXPECTED, "members_verified": 659, "copies": copies, "old_prototype": identity(D / "old/replay/corrected/replay/prototype.py"), "new_prototype": identity(source), "patch": identity(D / "source.patch"), "only_source_delta": "One post-loop full-completion check; no extra read, limit, cleanup, child or ownership changes."}, indent=2) + "\n")
print(json.dumps({"status": "prepared", "new_source": identity(source)}))
