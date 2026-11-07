"""Retain full MIR and exact artifact hashes, remove only owned build scratch."""
from pathlib import Path
import gzip,hashlib,json,os,shutil
HERE=Path(__file__).resolve().parent

def row(p):
 raw=p.read_bytes();return dict(path=str(p.relative_to(HERE)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
 build=HERE/'build';assert build.is_dir() and not build.is_symlink()
 outputs=[row(p) for p in sorted(build.rglob('*')) if p.is_file()]
 raw=(build/'actual.mir').read_bytes();dest=HERE/'commands/production-final/full.mir.gz';dest.write_bytes(gzip.compress(raw,mtime=0))
 assert gzip.decompress(dest.read_bytes())==raw
 artifact=dict(removed_artifacts=outputs,full_MIR_archive=row(dest),full_MIR_raw_bytes=len(raw),full_MIR_raw_sha256=hashlib.sha256(raw).hexdigest(),only_owned_build_directory_removed=str(build),native_or_foreign_processes_touched=False)
 (HERE/'artifact-retention.json').write_text(json.dumps(artifact,sort_keys=True,indent=2)+'\n')
 shutil.rmtree(build);assert not build.exists()
 print(json.dumps(dict(removed_build_files=len(outputs),full_MIR_retained=True,owned_build_absent=True)))
