# Correct the sole-parent proof

Independent source review found that HEAD^ reports only the first parent. The original templates therefore did not prove that the delivery commit has exactly one parent.

This correction changes only the committed-head argument to HEAD^@ in the common source template and both delivery argv forms. The existing delivery driver keeps head, tree, parent unpacking. A commit with zero or multiple parents cannot satisfy that unpacking before push. The parent must still equal the fixed baseline. The delivery remains exactly 23 commands.

The original 16 files and preparation.json remain frozen. owned.py and all custody, startup, kernel wait, EOF, latch, and signal logic remain unchanged. The corrected common template still refuses on line 1. This preparation performs no execution and creates no authority or final selection. exact.diff records every changed line.

Root final selection includes inert templates, this correction, owned.py, selected public evidence, product source, workflow source, tracking, and the separate selection file. Root excludes all four materialized Python drivers, all three materialized argv manifests, dynamic authorities, receipts, state, and the final source review. The runtime common module can continue to pin the selection hash. Root source review and authority bind the exact materialized sources and argv separately.

Root independently checks pending Git operation markers as data before admission. This correction adds no command or wider Git gate.
