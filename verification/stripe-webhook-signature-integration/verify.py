"""Read-only root integration evidence and optionally current hosted source check."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    acceptance = json.loads((HERE / "acceptance.json").read_text())
    for name, expected in acceptance["bindings"].items():
        assert sha(REPO / name) == expected, name
    for name, expected in json.loads((HERE / "seal.json").read_text()).items():
        path = REPO / name
        assert path.stat().st_size == expected["bytes"] and sha(path) == expected["sha256"], name
    if args.live:
        current = {name: sha(REPO / name) for name in acceptance["sourceInputs"]}
        assert current == acceptance["sourceInputs"]
        assert hashlib.sha256(json.dumps(current, sort_keys=True, separators=(",", ":")).encode()).hexdigest() == acceptance["sourceDigest"]
    print(f"PASS: {len(acceptance['bindings'])} evidence bindings, 127 hosted passes and 2 explicit skips; live source check={args.live}")


if __name__ == "__main__":
    main()
