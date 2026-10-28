from pathlib import Path
p=Path('hosted/scripts/test-identity-network.py');s=p.read_text()
needle='def validate_rebar_transfer(observed, download):'
validator='''def validate_bootstrap_export(tool, data, expected_bytes):
    require(tool in BOOTSTRAP and type(data) is bytes and type(expected_bytes) is int and 0 < expected_bytes <= 16777216, "bootstrap export input shape/bound")
    require(len(data) == expected_bytes, "observed bootstrap artifact byte-count mismatch")
    require(hashlib.sha512(data).hexdigest() == BOOTSTRAP[tool]["sha512"], "observed bootstrap artifact digest mismatch")
    return data


'''
assert needle in s;s=s.replace(needle,validator+needle)
old='''        literal = "path = " + json.dumps(path) + "; true = File.stat!(path).size <= " + str(maximum) + "; IO.binwrite(File.read!(path))"
        scratch = self.output / ".scratch" / "copy.bin"
        result, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "-e", literal], 30, limit=maximum, binary_path=scratch)
        scratch.unlink()
        return result'''
new='''        literal = "path = " + json.dumps(path) + "; true = File.stat!(path).size <= " + str(maximum) + "; :ok = :io.setopts(:standard_io, encoding: :latin1); :ok = IO.binwrite(File.read!(path))"
        public_tool = {"/workspace/downloads/hex.ez": "hex", "/workspace/tooling/rebar3": "rebar"}.get(path)
        if public_tool is not None:
            require(maximum <= 16777216, "public bootstrap export cap")
            destination = self.output / "bootstrap-exports" / (public_tool + "-actual.bin")
            destination.parent.mkdir(exist_ok=True)
            require(not destination.exists(), "public bootstrap export already retained")
        else:
            destination = self.output / ".scratch" / "copy.bin"
        try:
            result, _, _ = self.execute(owned, ["/usr/local/bin/elixir", "-e", literal], 30, limit=maximum, binary_path=destination)
        finally:
            # Only these two fixed public artifacts survive a failed host check.
            # Partial command captures remain partial; they cannot be a tool pass.
            if public_tool is not None and destination.is_file():
                require(destination.stat().st_size <= maximum, "retained public bootstrap capture cap")
                body = destination.read_bytes()
                log = self.output / "logs" / f"{self.command_number:04d}.json"
                command = json.loads(log.read_bytes()) if log.is_file() else {}
                write_json(destination.with_suffix(".json"), {"schema": 1, "tool": public_tool, "container_path": path, "owned_cid": owned.cid, "role": owned.role, "command_number": self.command_number, "maximum_bytes": maximum, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "sha512": hashlib.sha512(body).hexdigest(), "expected_sha512": BOOTSTRAP[public_tool]["sha512"], "stdout_complete": command.get("stdout_complete"), "stderr_complete": command.get("stderr_complete"), "command_exit_code": command.get("exit_code"), "qualification": "bounded-public-command-stdout-only-before-host-size-and-digest-validation"})
        if public_tool is None:
            destination.unlink()
        return result'''
assert old in s;s=s.replace(old,new)
s=s.replace('''            require(hashlib.sha512(artifact).hexdigest() == BOOTSTRAP[tool]["sha512"], "observed bootstrap artifact digest mismatch")''','''            validate_bootstrap_export(tool, artifact, bootstrap_result[tool]["bytes"])''')
p.write_text(s)
