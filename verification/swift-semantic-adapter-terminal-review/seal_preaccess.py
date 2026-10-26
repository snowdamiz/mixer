"""Seal the immutable preparation; never reads the new correction."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "preaccess"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if (OUT / "seal.json").exists():
        raise RuntimeError("Existing preaccess seal must remain immutable")
    # Snapshot the now-reviewable document into the immutable preparation. The
    # live document can later report the admitted review without changing it.
    document = ROOT / "docs/swift-semantic-adapter-terminal-review.md"
    (OUT / "prepared-review-document.md").write_bytes(document.read_bytes())
    (OUT / "source/seal_preaccess.py.txt").write_bytes(Path(__file__).read_bytes())
    # git diff does not see untracked files; use an explicit owned-text check.
    inspected=[]
    for path in sorted(OUT.rglob("*")):
        if not path.is_file(): continue
        if path.relative_to(OUT).parts[0] in {"original-inputs","bootstrap","commands"}: continue
        raw=path.read_bytes()
        try: text=raw.decode("utf-8")
        except UnicodeDecodeError: continue
        bad=[i for i,line in enumerate(text.splitlines(),1)
             if line.rstrip(" \t")!=line]
        assert not bad, (path,bad)
        inspected.append(str(path.relative_to(OUT)))
    (OUT/"whitespace-check.json").write_text(json.dumps({
        "scope":"explicit owned preaccess text files, including untracked",
        "files_checked":inspected,"trailing_whitespace_findings":0,
        "Rust_product_tests":0},indent=2)+"\n")
    command=["python3","verification/swift-semantic-adapter-terminal-review/seal_preaccess.py"]
    (OUT/"seal-command.json").write_text(json.dumps({
        "argv":command,"cwd":str(ROOT),"scope":"preaccess preparation only",
        "new_correction_opened":False,"exit_receipt":"successful output is seal.json plus seal.sha256; verification follows read-only"},indent=2)+"\n")
    members=[]
    for path in sorted(OUT.rglob("*")):
        if not path.is_file() or path in {OUT/"seal.json",OUT/"seal.sha256"}: continue
        data=path.read_bytes()
        members.append({"path":str(path.relative_to(OUT)),"bytes":len(data),"sha256":sha(data)})
    seal={"schema":1,"scope":"immutable independent R1 preaccess plan/cases/source custody; no correction access",
          "excluded":["seal.json","seal.sha256"],"member_count":len(members),
          "member_bytes":sum(m["bytes"] for m in members),"members":members}
    content=(json.dumps(seal,indent=2,sort_keys=True)+"\n").encode()
    (OUT/"seal.json").write_bytes(content)
    (OUT/"seal.sha256").write_text(sha(content)+"  seal.json\n")
    print(json.dumps({"preaccess_seal_sha256":sha(content),"members":len(members),
                      "member_bytes":seal["member_bytes"],
                      "plan_sha256":sha((OUT/"plan.md").read_bytes()),
                      "cases_sha256":sha((OUT/"cases.json").read_bytes()),
                      "correction_accessed":False},indent=2))


if __name__=="__main__":
    main()
