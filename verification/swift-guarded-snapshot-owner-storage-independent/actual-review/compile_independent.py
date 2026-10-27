"""Bounded fresh metadata only; does not import or execute producer code."""
from pathlib import Path
import hashlib, json, os, signal, subprocess, time, sys, platform

HERE = Path(__file__).resolve().parent
V = HERE.parents[1]
SOURCE = V / "swift-guarded-snapshot-scope-authority-correction/source/vm"
RUSTC = Path("/Users/andreyyurlov/.rustup/toolchains/1.99.0-aarch64-apple-darwin/bin/rustc")
sha = lambda b: hashlib.sha256(b).hexdigest()


def main():
    assert sha((V/"swift-guarded-snapshot-owner-storage-closure/seal.json").read_bytes()) == "afd33c1df35e4072e582789a38c14372f9a8efc4c6243301df4399e4899f2e4b"
    assert sha((V/"swift-semantic-adapter-root-review/guarded-snapshot-owner-storage-independent-release.json").read_bytes()) == "179657104fe9d848d4cb816fd4a703551af624a88e2a97b6d2c67cf6d4a3669c"
    manifest = json.loads((SOURCE.parents[1]/"source-manifest.json").read_text())
    for m in manifest["members"]:
        b=(SOURCE/m["path"]).read_bytes()
        assert (len(b),sha(b)) == (m["bytes"],m["sha256"])
    work=HERE/"owned-work"
    work.mkdir(exist_ok=True)
    version=subprocess.run([str(RUSTC),"--version","--verbose"],capture_output=True,check=True,timeout=10).stdout.decode()
    contexts=["baseline"] if sys.argv[1:]==["--baseline-only"] else ["production","unit"]
    for context in contexts:
        selected_source=SOURCE
        selected_tree=manifest["source_tree_sha256"]
        if context=="baseline":
            selected_source=V/"swift-guarded-snapshot-encoder-implementation/source/vm"
            baseline=json.loads((V/"swift-guarded-snapshot-owner-storage-closure/baseline-custody.json").read_text())
            for m in baseline["members"]:
                b=(selected_source/m["path"]).read_bytes()
                assert (len(b),sha(b))==(m["bytes"],m["sha256"])
            selected_tree=baseline["accepted_source_tree_sha256"]
        command_dir=HERE/"commands"/context
        command_dir.mkdir(parents=True,exist_ok=False)
        output=work/(context+".mir")
        argv=[str(RUSTC),"--crate-name","mixer_vm","--edition=2021","--target","aarch64-apple-darwin","-C","opt-level=0","-C","overflow-checks=yes","-C","panic=unwind"]
        for feature in ["experimental-swift-reactor","experimental-swift-wasi","experimental-stream-validation","experimental-function-cache"]:
            argv += ["--cfg",'feature="'+feature+'"']
        argv += (["--test"] if context=="unit" else ["--crate-type","rlib"])
        argv += [str(selected_source/"src/lib.rs"),"--emit=mir","-Zmir-opt-level=0","-Zmir-include-spans=yes","-o",str(output)]
        env={"PATH":"/usr/bin:/bin","TMPDIR":str(work),"CARGO_MANIFEST_DIR":str(selected_source),"RUSTC_BOOTSTRAP":"1"}
        started=time.monotonic(); child=subprocess.Popen(argv,cwd=V.parent,env=env,start_new_session=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        actions=[]; timed_out=False
        try: stdout,stderr=child.communicate(timeout=55)
        except subprocess.TimeoutExpired:
            timed_out=True
            for sig in [signal.SIGTERM,signal.SIGKILL]:
                try:os.killpg(child.pid,sig);actions.append(sig.name)
                except ProcessLookupError:pass
                try:stdout,stderr=child.communicate(timeout=2);break
                except subprocess.TimeoutExpired:continue
            else:raise AssertionError("owned compiler group failed to stop")
        try:os.killpg(child.pid,0);absent=False
        except ProcessLookupError:absent=True
        for name,data in [("stdout",stdout),("stderr",stderr)]: (command_dir/name).write_bytes(data)
        receipt=dict(schema=1,context=context,argv=argv,cwd=str(V.parent),environment=env,python_version=platform.python_version(),rustc_version=version,compiler_sha256=sha(RUSTC.read_bytes()),timeout_seconds=55,elapsed_seconds=time.monotonic()-started,exit_code=child.returncode,owned_process_group=child.pid,owned_group_absent=absent,child_reaped=True,timed_out=timed_out,cleanup_actions=actions,stdout_sha256=sha(stdout),stderr_sha256=sha(stderr),source_tree_sha256=selected_tree,source_members=144,output_bytes=output.stat().st_size if output.exists() else None,output_sha256=sha(output.read_bytes()) if output.exists() else None,scope="host compiler MIR only; no product dispatch, native/UI/capture/global inventory")
        (command_dir/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        print(json.dumps({k:receipt[k] for k in ["context","exit_code","elapsed_seconds","owned_group_absent","output_bytes"]}),flush=True)
        assert not timed_out and child.returncode==0 and absent


if __name__ == "__main__":main()
