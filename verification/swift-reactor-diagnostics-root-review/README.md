# Root review of exact Swift reactor diagnostics

The final audit binds 150 current source, command-output, tool and artifact paths,
including compressed and decompressed per-function inventory. No missing path or
hash mismatch remains in `audit.json`. `initial-audit.json` retains the discovery
that the first trace collector referenced Cargo's mutable executable path, which
had since been rebuilt. Root changed that collector to preserve its exact tool
before execution and reran the complete strict rejection, diagnostic inventory,
and Node reference trace in `2026-10-23-retained-tool`. The earlier receipt is
historical evidence and is not silently repaired or treated as a current binary
binding. The retained executable remains a diagnostic tool without an asserted
current-source build relationship.

The exact reactor still has 79,832 defined bodies, 34 imports, 6,505,659 raw
instructions, 584 initial memory pages and 46,713 table entries. All bodies are
inventoried; 79,826 individually decode under the existing diagnostic ceiling and
six exceed its control-depth limit. The maximum raw depth is 378 nested blocks,
or 379 including the function frame. Parameters plus locals peak at 181. The
reported operand-height maximum of 67 is scalar-arity inventory, not complete
type validation or a runtime stack measurement. The compatibility run preserves
the original command artifact's complete 79,837-body inventory.

The development reference executes initialization once and the unchanged
11-observation corpus twice, retaining complete equality. Its exact import trace
informs the separately bounded WASI adapter. It does not authorize imports or
prove execution in the owned interpreter. The unchanged strict profile rejects
the reactor's 53,777,114 source bytes; its 18,976,211 compressed bytes still exceed
the product's 3 MiB target. Full owned validation/execution, dynamic live-stack and
cache behavior, mobile performance, immutable release consumption and GA remain
open. No physical device was queried or run.

Run `python3 verification/swift-reactor-diagnostics-root-review/audit.py` to check
the retained bindings. Both final diagnostic drivers retain their tool binaries
under ignored local directories, so a future cleanup must be reported as missing
evidence rather than silently passing the audit.
