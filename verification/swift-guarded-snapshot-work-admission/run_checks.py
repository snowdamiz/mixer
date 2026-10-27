"""Record the bounded finite custody checker and its exact command output."""
import gzip
import json
import sys
from prepare import HERE,ROOT,sha
from run import bounded

def main():
    assert not (HERE/'seal.json').exists()
    folder=HERE/'commands/finite-source-controls';folder.mkdir(parents=True,exist_ok=False)
    argv=[sys.executable,'-B',str(HERE/'check.py')]
    out,err,r=bounded(argv,{'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'},ROOT,20)
    (folder/'stdout.gz').write_bytes(gzip.compress(out,mtime=0));(folder/'stderr').write_bytes(err)
    r.update(schema=1,python=sys.version,python_executable=sys.executable,driver_sha256=sha((HERE/'run_checks.py').read_bytes()),
        checker_sha256=sha((HERE/'check.py').read_bytes()),stdout_sha256=sha(out),stderr_sha256=sha(err),
        source_tree_sha256=json.loads((HERE/'source-manifest.json').read_text())['source_tree_sha256'],
        scope='finite custody/source/ordering check; no product runtime')
    (folder/'receipt.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    assert r['exit_code']==0 and r['owned_group_absent'] and not r['timed_out'],err.decode()
    print(out.decode().strip())

if __name__=='__main__':main()
