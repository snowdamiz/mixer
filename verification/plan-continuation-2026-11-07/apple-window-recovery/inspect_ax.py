"""One nonmutating public AX inventory of the exact newly opened frontend."""
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / 'apple-safe-keyboard-fix-r3'))
from mac_backend import AX

ax = AX()
result = {'pid': 75452, 'trusted': ax.trusted(), 'windows': [], 'mutations': 0}
try:
    if result['trusted'] is not True:
        raise RuntimeError('Fresh public AX trust unavailable')
    app = ax.app(75452)
    for window in ax.children(app, 'AXWindows', False):
        result['windows'].append({
            'identifier': ax.text(window, 'AXIdentifier', True),
            'title': ax.text(window, 'AXTitle'),
            'role': ax.text(window, 'AXRole'),
            'main': ax.flag(window, 'AXMain'),
        })
except BaseException as error:
    result['error'] = repr(error)
finally:
    ax.release()
print(json.dumps(result))
