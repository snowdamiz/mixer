#!/usr/bin/env python3
"""Exhaustive small index proof only, not a pin/frame/cache runtime fixture."""
import json
count=0
for size in range(13):
    original=list(range(size))
    for reject_mask in range(1 << size):
        for already_processed_top in [False, True] if size else [False]:
            if already_processed_top and not (reject_mask & (1 << (size-1))):
                continue
            arena=original.copy()
            remaining=size-int(already_processed_top)
            visited=[size-1] if already_processed_top else []
            while remaining:
                assert arena[:remaining] == original[:remaining]
                assert all(reject_mask & (1 << identity) for identity in arena[remaining:])
                remaining -= 1
                frame=arena.pop(remaining)
                assert frame==remaining
                visited.append(frame)
                if reject_mask & (1 << frame):
                    arena.insert(remaining,frame)
            assert visited==list(reversed(original))
            assert arena==[i for i in original if reject_mask & (1 << i)]
            count += 1
print(json.dumps(dict(status='pass-index-model-only',cases=count,maxSize=12,
    realFrames=False,realPins=False,runtimeAcceptance=False),sort_keys=True))
