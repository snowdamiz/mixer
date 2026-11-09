"""Keep Python class declarations importable while denying every constructor."""
import subprocess

def install(guard, write_root):
    process_type = subprocess.Popen
    guard.install(write_root)
    if isinstance(process_type, type):
        def denied_constructor(self, *args, **kwargs):
            guard.DENIED.append('Popen constructor')
            raise RuntimeError('Metadata diagnostics forbid process construction')
        process_type.__init__ = denied_constructor
        subprocess.Popen = process_type
