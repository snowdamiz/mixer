#!/usr/bin/env python3
"""Close the first-frame overlay against both pinned source trees."""
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
PATCH = SOURCE / "android-first-frame-trace.patch"
PATCH_SHA256 = "4ea4c46c411b38e7615c76c72d60ae9d4d2bcd50c45f3d71659423f1fee8684c"
PREIMAGE_TREE = "8d37af63e780cbcffeb97f5f8c8ede2bf0e19f9f"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(repo, *args):
    return subprocess.check_output(["git", "-C", repo, *args], text=True, timeout=30).strip()


def main(work, derive):
    require(sha256(PATCH.read_bytes()).hexdigest() == PATCH_SHA256, "Wrong fixture patch")
    prior = json.loads((SOURCE / "reference/prior-renderer-capture.json").read_bytes())
    require(git(work / "fieldlog", "write-tree") == PREIMAGE_TREE, "Wrong FieldLog preimage tree")
    files = re.findall(
        r"^diff --git a/(fieldlog|mixer)/(\S+) b/\1/\2\nindex ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644$",
        PATCH.read_text(), re.M,
    )
    require(len(files) == 7, "Wrong fixture file count")
    require(sum(repo == "fieldlog" for repo, *_ in files) == 3, "Wrong FieldLog fixture file count")
    for repo, name, before, _ in files:
        path = work / repo / name
        key = ("app/" if repo == "fieldlog" else "mixer/") + name
        require(git(work / repo, "hash-object", path) == before
                and sha256(path.read_bytes()).hexdigest() == prior["linkFiles"][key],
                f"Wrong preimage for {key}")
    git(work / "fieldlog", "apply", "--index", "-p2", "--include=Integrations/**", PATCH)
    git(work / "mixer", "apply", "-p2", "--include=capability-activation/**",
        "--include=experimental-capability-runtime/**", PATCH)
    hashes = {}
    fallback = prior["fallbackFiles"].copy()
    for repo, name, _, after in files:
        path = work / repo / name
        key = ("app/" if repo == "fieldlog" else "mixer/") + name
        require(git(work / repo, "hash-object", path) == after, f"Wrong postimage for {key}")
        hashes[key] = sha256(path.read_bytes()).hexdigest()
        if repo == "fieldlog":
            require(name in fallback, f"Wrong fallback path {name}")
            fallback[name] = hashes[key]
    fallback_sha = sha256("".join(f"{value}  {name}\n" for name, value in sorted(fallback.items())).encode()).hexdigest()
    pins = {
        "fieldLogTree": git(work / "fieldlog", "write-tree"),
        "fallbackSHA256": fallback_sha,
        "firstFrameSourceSHA256": hashes,
    }
    if not derive:
        expected = json.loads((SOURCE / "diagnostic-pins.json").read_bytes())
        require(pins == {key: expected[key] for key in pins}, "First-frame source closure differs")
    print(json.dumps(pins, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve(strict=True), sys.argv[2:] == ["--derive"])
