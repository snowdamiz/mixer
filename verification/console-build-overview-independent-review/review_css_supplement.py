"""Bind the narrow root-owned responsive CSS correction without replaying tests."""
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import platform
import sys

PACKET = Path(__file__).resolve().parent
ROOT = PACKET.parent.parent
SOURCE = "console/src/styles.css"
BEFORE = "41a5556367ed75845d4884efe1fa0a752c5379bd6824f60ecac0dd28c8c666c5"
AFTER = "bd2a2506c6ec666d4fc9282e5e81ae74fd8fcf46f5d8a64c56c070bf1b9c25b0"


def sha(data):
    return hashlib.sha256(data).hexdigest()


prior_receipt = (PACKET / "receipt.json").read_bytes()
prior_manifest_data = (PACKET / "source-manifest.json").read_bytes()
prior_manifest = json.loads(prior_manifest_data)
root_note = ROOT / "verification/console-build-overview-root-review/responsive-refinement.json"
note_data = root_note.read_bytes()
note = json.loads(note_data)
assert note["beforeSHA256"] == BEFORE and note["afterSHA256"] == AFTER
before = (PACKET / "source-snapshot" / SOURCE).read_bytes()
after = (ROOT / SOURCE).read_bytes()
assert sha(before) == BEFORE and sha(after) == AFTER
old_label = ".preview-banner label { display: flex; align-items: center; gap: 10px; font-size: 11px; white-space: nowrap; }"
new_label = old_label[:-2] + " max-width: 100%; }"
old_select = ".preview-banner select { padding: 6px 26px 6px 9px; background: var(--white); border: 1px solid #d9cbbb; border-radius: 6px; color: #4d5148; font-size: 11px; max-width: 100%; }"
new_select = old_select[:-2] + " min-width: 0; flex: 1; }"
text = before.decode()
assert text.count(old_label) == 1 and text.count(old_select) == 1
expected = text.replace(old_label, new_label).replace(old_select, new_select).encode()
assert after == expected, "CSS contains a change outside the two expected declarations"
current = {relative: sha((ROOT / relative).read_bytes()) for relative in prior_manifest["files"]}
changed = [relative for relative, digest in current.items() if digest != prior_manifest["files"][relative]]
assert len(current) == 28 and changed == [SOURCE], changed
new_digest = sha("".join(f"{path}\0{digest}\n" for path, digest in current.items()).encode())
diff = "".join(difflib.unified_diff(text.splitlines(keepends=True), after.decode().splitlines(keepends=True), fromfile="captured/console/src/styles.css", tofile="current/console/src/styles.css"))
(PACKET / "css-supplement.diff").write_text(diff)
(PACKET / "styles-after.css").write_bytes(after)
(PACKET / "root-responsive-refinement.json").write_bytes(note_data)
summary = {"outcome": "passed narrow source comparison; root owns runtime/build verification", "changedInputCount": len(changed), "comparedInputCount": len(current), "changedInputs": changed, "sourceTreeDigestAfter": new_digest, "priorReceiptPreserved": True}
stdout = json.dumps(summary, indent=2) + "\n"
receipt = {"schema": 1, "recordedAt": datetime.now(timezone.utc).isoformat(), **summary,
    "command": {"argv": ["python3", "-B", "verification/console-build-overview-independent-review/review_css_supplement.py"], "cwd": str(ROOT), "exitCode": 0,
        "toolVersion": platform.python_version(), "pythonExecutable": sys.executable, "stdout": "css-supplement.stdout", "stdoutSha256": sha(stdout.encode()), "stderr": "css-supplement.stderr", "stderrSha256": sha(b"")},
    "baseRevision": prior_manifest["baseRevision"], "priorSourceTreeDigest": prior_manifest["treeDigest"],
    "priorReceiptSha256": sha(prior_receipt), "priorManifestSha256": sha(prior_manifest_data),
    "sourcePath": SOURCE, "sourceSha256Before": BEFORE, "sourceSha256After": AFTER,
    "sourceComparison": {"expectedLabelDelta": "max-width: 100%", "expectedSelectDelta": "min-width: 0; flex: 1", "exactExpectedTransformationMatches": True,
        "allOther27InputsUnchanged": True, "brandLogoFaviconAndEffectiveTokensUnchanged": True, "domainComponentsPreviewAndAppUnchanged": True},
    "currentInputHashes": current,
    "artifactHashes": {"review_css_supplement.py": sha(Path(__file__).read_bytes()), "css-supplement.diff": sha(diff.encode()), "styles-after.css": sha(after), "root-responsive-refinement.json": sha(note_data)},
    "limitations": ["Source-only CSS supplement; the previous seven-control/typecheck/build receipt remains bound to its original pre-refinement snapshot.", "No test/build replay or browser execution here; root owns fresh select containment and production build receipts.", "No customer API/authentication/authorization, native/device, hosting, signing, distribution or GA acceptance."],
    "cleanup": {"temporaryFilesCreated": 0, "serversStarted": 0, "browserSessionsStarted": 0, "nativeInstancesStarted": 0, "networkOperations": 0, "gitOperations": 0}}
assert (PACKET / "receipt.json").read_bytes() == prior_receipt
assert (PACKET / "source-manifest.json").read_bytes() == prior_manifest_data
(PACKET / "css-supplement.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(stdout, end="")
