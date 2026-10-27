"""Pure finite source-work proposal. Does not load, validate, compile or grant."""
from dataclasses import dataclass
import json
from pathlib import Path

U64 = (1 << 64) - 1
CAPS = dict(source=67108864, build=131072, session=65536, executable=67108864,
            metadata=16777216, scratch=1048576, credits=512000000, deadline=120000)
P, K, N, A, BLOCK = 16384, 4096, 64, 32, 4096
ROOT = Path(__file__).resolve().parent

class Refused(ValueError): pass

def natural(x):
    if type(x) is not int or not 0 <= x <= U64: raise Refused('not-u64')
    return x

def add(*xs):
    result = 0
    for x in xs:
        natural(x)
        if result > U64 - x: raise Refused('add-overflow')
        result += x
    return result

def mul(x, y):
    natural(x); natural(y)
    if x and y > U64 // x: raise Refused('mul-overflow')
    return x * y

def ceil_blocks(x):
    natural(x)
    return add(x // BLOCK, int(x % BLOCK != 0))

@dataclass(frozen=True)
class Geometry:
    source: int
    build: int
    session: int
    executable: int
    validator_source: int
    metadata: int
    scratch: int
    credits: int
    deadline: int

    def checked(self):
        for name in ('source','build','session','executable','metadata','scratch','credits','deadline'):
            value = natural(getattr(self, name))
            if value > CAPS[name]: raise Refused('cap:' + name)
        natural(self.validator_source)
        if self.validator_source > CAPS['source'] or self.source > self.validator_source:
            raise Refused('validator-source')
        return self

