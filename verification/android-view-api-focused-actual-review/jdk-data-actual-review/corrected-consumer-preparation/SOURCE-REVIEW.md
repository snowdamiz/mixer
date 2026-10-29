# Corrected consumer source preparation

The original controller was aborted once under explicit root cleanup authority; its signal is now aborted. That signal state does not independently confirm transport EOF. The original failed acquisition packet and source-inspection packet remain unchanged.

The candidate declares one consumer function and a retained private state object. Controller, response, reader and timer remain available throughout finally. It checks Content-Length by exact string equality with 5904159, reads under an 8 MiB cap and one 20-second deadline, and accepts only the exact 5,904,159-byte payload with SHA256 b166c2e2ce0dbff158315166ce407cd21915e560fcb22577ffd1630f1556cfb0. The deadline races fetch, reads and cancellation.

Finally attempts cancellation on each non-EOF response, including header rejection before reader creation, and releases an existing reader. Failed cancellation keeps the deadline armed until it fires. Only EOF plus successful reader release permits writing the payload. Reduced receipts contain no full response, signed URL or raw error message. Private retained Response objects may contain URL metadata in memory; they must not be printed or serialized.

Nine finite source-text checks pass. No candidate evaluation, synthetic execution, connector call, transfer or recovery invocation occurred. These are source checks, not runtime evidence. The 20-second deadline governs network/stream await paths; local data writes have no separate deadline. Runtime stream behavior and independent transport EOF remain unproved. Root must separately select recovery before this source is loaded or called. No Java/compiler/native/UI/capture/process/held-resource operation is authorized by this preparation.
