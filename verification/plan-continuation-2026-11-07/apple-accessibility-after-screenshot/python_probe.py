import ctypes
import json
import os
import sys

api = ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
api.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
api.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
print(json.dumps({'trusted': bool(api.AXIsProcessTrustedWithOptions(None)),
                  'pid': os.getpid(), 'executable': sys.executable, 'prompt': False}))
