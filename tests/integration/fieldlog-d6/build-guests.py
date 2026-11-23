#!/usr/bin/env python3
"""Rebuild the two D6 release payloads with the pinned Embedded Swift tools."""
import argparse
import hashlib
from pathlib import Path

from prepare import HERE, digest, private_env, require, run, write

PAYLOAD_PREFIXES = {
    "baseline": (5489, "5447846d533dda7cc140f6f468180ea4d5fba28e0f95066a751fb7aaaa65ab3f"),
    "staged": (5521, "2fb1b7ed5ec3ef01bb7fc8814047c9ea3badc81f64af2338eb6f09643e1b9932"),
}


def build(toolchain, output):
    output.mkdir(mode=0o700)
    env = private_env(output)
    source = HERE / "guest"
    swift = run([toolchain / "swiftc", "--version"], env).decode().strip()
    linker = run([toolchain / "wasm-ld", "--version"], env).decode().strip()
    require("6.3.3 (swift-6.3.3-RELEASE)" in swift and "LLD 21.0.0" in linker, "guest toolchain differs")
    shim = output / "CapabilityImports.o"
    run([toolchain / "clang", "--target=wasm32-unknown-none", "-ffreestanding", "-Oz",
         "-c", source / "CapabilityImports.c", "-o", shim], env)
    exports = ["start", "event", "hydrate"]
    payloads = {}
    for name, define in (("baseline", "BASELINE"), ("staged", "REQUIRE_REVIEW")):
        obj, wasm = output / f"{name}.o", output / f"{name}.wasm"
        run([toolchain / "swiftc", "-target", "wasm32-unknown-none-wasm",
             "-enable-experimental-feature", "Embedded", "-enable-experimental-feature", "Extern",
             "-whole-module-optimization", "-Osize", "-parse-as-library", "-Xfrontend",
             "-disable-stack-protector", "-D", define, "-emit-object", source / "Guest.swift",
             source / "TaskWire.swift", "-o", obj], env)
        run([toolchain / "wasm-ld", "--no-entry", "--gc-sections", "--strip-all", "-z",
             "stack-size=16384", "--max-memory=65536", *[f"--export=mixer_guest_ui_{e}_v1" for e in exports],
             "--export=mixer_guest_capability_ready_v1", obj, shim, "-o", wasm], env)
        data = wasm.read_bytes()
        require((len(data), hashlib.sha256(data[:-16]).hexdigest()) == PAYLOAD_PREFIXES[name],
                f"{name} guest differs outside the trailing 16 data bytes")
        payloads[name] = digest(wasm)
    write(output / "receipt.json", {"swift": swift, "linker": linker, "payloads": payloads})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("toolchain_bin", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.toolchain_bin.resolve(strict=True), args.output.absolute())
