from pathlib import Path
import json
import subprocess as sp
import sys

work = Path(sys.argv[1])
inputs = [
    ("swift-asn1", "3b6410f7dee09eb33cdd26260c5fd47fda19b0e2", "e7ed2e8c1483426c349b678e7d10940509f9d39c"),
    ("swift-crypto", "c2cbadd7263439d8015189668f96ff5b5be565ce", "841fdfd88fed694e6532a3200a91b0f85595c340"),
]
for name, commit, tree in inputs:
    root = work / name
    root.mkdir()
    sp.run(["git", "init", "-q", root], check=True)
    sp.run(["git", "-C", root, "fetch", "-q", "--no-tags", "--depth=1",
            f"https://github.com/apple/{name}.git", commit], check=True)
    sp.run(["git", "-C", root, "checkout", "-q", "--detach", "FETCH_HEAD"], check=True)
    assert sp.check_output(["git", "-C", root, "log", "-1", "--format=%H %T"]
                           ).decode().strip() == f"{commit} {tree}"
    print(name, commit, tree)
sdk = work / "mixer/sdk"
for target in [sdk, work / "mixer/updates"]:
    manifest = target / "Package.swift"
    text = manifest.read_text()
    old = '.package(url: "https://github.com/apple/swift-crypto.git", exact: "5.0.3")'
    assert text.count(old) == 1, manifest
    manifest.write_text(text.replace(old, f'.package(path: "{work}/swift-crypto")'))
