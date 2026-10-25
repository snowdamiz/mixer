#!/usr/bin/env python3
"""Seal this bounded build lane once, without changing its accepted inputs."""
import datetime
import hashlib
import json
from pathlib import Path
import stat

B = Path(__file__).resolve().parent
R = B.parents[1]
assert not (B / "handoff.json").exists() and not (B / "handoff.sha256").exists()
assert not (B / "attempt-1/owned-build").exists()
files = [R / "docs/apple-settings-fixed-chunk-native-build.md"] + sorted(p for p in B.rglob("*") if p.is_file())
members = {}
for p in files:
    s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_nlink == 1
    raw = p.read_bytes()
    members[str(p.relative_to(R))] = dict(kind="file", mode=stat.S_IMODE(s.st_mode), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
receipt = json.loads((B / "attempt-1/receipt.json").read_bytes())
assert receipt["passed"] and receipt["ownedScratchRemoved"]
handoff = dict(schema=1, observedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope="fresh root-selected fixed4992 generic simulator runner build only", controllerSourceRevision=receipt["controllerSourceRevision"], rootSelectionSHA256="2addcd0f2b37463241cec8451b444cb4b933ce5dfcf5b2f0ecec483aae2b7db8", producerHandoffSHA256="2d01866f3fa0f88b283ba8f2774f03092eb93d9616daeaa7d5d2875618cf6748", reviewHandoffSHA256="43f2ee87e461d28a8d05d113adf7a9581ea34c6d16e0dfe5caee26773febc092", sourceArchiveSHA256=receipt["sourceArchive"]["sha256"], productArchiveSHA256=receipt["productArchive"]["sha256"], sourceTreeSHA256=receipt["sourceTreeSHA256"], productTreeSHA256=receipt["productTreeSHA256"], sourceFiles=40, products=55, originalApplicationFilesUnchanged=13, runnerProductFilesFresh=42, warningLines=15, allWarningMessagesMatchOriginalAndPrior=True, ownedScratchRemoved=True, nativeExecuted=False, nativeExecutionSelected=False, importerRebound=False, physicalPhones="disconnected-deferred", gaAccepted=False, members=members)
raw = (json.dumps(handoff, indent=2, sort_keys=True) + "\n").encode()
(B / "handoff.json").write_bytes(raw)
digest = hashlib.sha256(raw).hexdigest()
(B / "handoff.sha256").write_text(digest + "\n")
print(json.dumps(dict(handoffSHA256=digest, sealedMembers=len(members), sourceArchiveSHA256=handoff["sourceArchiveSHA256"], productArchiveSHA256=handoff["productArchiveSHA256"]), sort_keys=True))
