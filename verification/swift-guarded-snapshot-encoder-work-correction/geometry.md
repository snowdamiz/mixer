# Counter bounds and finite reference controls

Let H=2560, T=4096, S be source bytes, n_sid the eight metadata counts, w_sid
their fixed widths [3,1,5,3,4,4,4,4]. Let L=sum(w_sid*n_sid), M=H+S,
E=M+8L, B=ceil(E/T). The opaque cursor constructs contiguous directories and
checks E <= 69,765,152 at initialization. Zero-length sections are skipped by
the search, not by assuming a record exists.

For a full successful traversal, every nonfinal returned block contains exactly
T bytes. The header branch intersects only block zero, because H<T: exactly one
header chunk. For S>0, the source branch has one visit for each block intersecting
[H,M), so

```
C = floor((M-1)/T) - floor(H/T) + 1
```

and C=0 when S=0. Each source visit selects directory zero on the first probe.
No source chunk is processed once per byte.

Each metadata iteration encodes the remainder of one logical 8-byte word.
Within each section, words and records begin on integral 8-byte offsets from M.
Every word is visited once, except when an internal block boundary cuts it.
Let K_sid count boundaries kT strictly inside the section whose offset from its
section start is nonzero modulo 8. Then

```
W_sid = w_sid*n_sid + K_sid
W = L + sum(K_sid)
I = 1 + C + W
D = C + sum((sid+1)*W_sid), sid=1..8
Q = E
```

All sections have the same alignment modulo 8 as S. Therefore K=0 when S%8=0.
Otherwise every internal metadata block boundary cuts exactly one word, and
K is the count of kT in (M,E); K <= B-1. A boundary coinciding with a section
boundary cuts no word (with S%8!=0 coincidence with kT is impossible). A word
split adds one visit; it does not cause a full-record or parameter rescan loop.
The entire record validation is nevertheless repeated by that visit.

For a single call, metadata word fragments partition at most 4096 bytes. A
possible initial partial word and final partial word give at most 513 visits.
There can additionally be at most one header and one source chunk, so I<=515.
Every directory range has nine entries, hence D<=9I; W<=513; Q<=4096. An early
fallible error stops sooner. Counting its attempted record visit consumes the
next fragment's slot; it cannot add a 514th visit after a full block. Even an
unreachable directory-not-found field error is costed after its nine probes.

`audit.py` independently models interval geometry, not private proof authority.
It checks all 32768 (skip, remaining-block-byte) combinations, every section
identity, zero sections, section transitions and every source ending alignment
modulo 4096. It compares loop/reference counters to the closed forms, checks
finite failure prefixes and malformed helper branches, and reads two frozen
actual artifacts as immutable geometry witnesses. It also computes the
independent maximum envelope without executing a maximum fixture.

A prefix that errors is bounded by the full traversal it would otherwise have
completed, provided the consumer stops on the first error. `emitted` stays at
the last successful block on error, so retrying the same block would repeat work.
No finite whole-stream bound authorizes arbitrary retries or extra None calls.
