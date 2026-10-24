#!/usr/bin/env python3
import pathlib
import sys
HERE = pathlib.Path(__file__).resolve().parent
V4 = HERE.parent / 'apple-toggle-keyboard-focus-v4'
sys.path.insert(0, str(V4))
source = (V4 / 'execute_v4_controls.py').read_text()
exec(compile(source, str(HERE / 'legacy44.py'), 'exec'), {'__name__': '__main__', '__file__': str(HERE / 'legacy44.py')})
