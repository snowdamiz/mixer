"""Root's future explicit subprocess; never invoked during host preparation."""
import importlib.util, json, sys
from pathlib import Path
from verify_bindings import verify, OLD, PACKET_SHA
from commands import write
if __name__=='__main__':
    verify()
    selection=Path(sys.argv[1]); expected_sha=sys.argv[2]
    write(selection.parent/'native-invocation-once.json',dict(packetSHA256=PACKET_SHA,selectionSHA256=expected_sha))
    spec=importlib.util.spec_from_file_location('unchanged_dispatch',OLD/'dispatch_successor.py')
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    result=mod.dispatch(PACKET_SHA,selection,expected_sha)
    write(selection.parent/'dispatch-result.json',result)
    print(json.dumps(result))
