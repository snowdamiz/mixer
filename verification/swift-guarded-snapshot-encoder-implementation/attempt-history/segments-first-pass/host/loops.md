Cursor initialization checks only fixed bounds: nine inventories, 34 resolved
enum values, five validation limits, 17 run limits, seven WASI limits, five grants,
12 absent-WASI words, and fixed header fields. It does not scan source or records.

Each next_block emits at most4096 bytes. Its progress loop executes at most515
iterations (up to513 metadata words plus fixed header and source chunks). A word
checks at most one record with five logical fields, two spans and one type index;
each iteration probes at most9 directories. There is no whole-record/source scan,
allocation, I/O, callback, stop/work grant or rewind. Failure leaves emitted_extent
at the last successfully returned block; caller transfer scratch is unspecified.
These are local loop ceilings only; original-control work/stop composition and
its formula remain separate pending implementation.
