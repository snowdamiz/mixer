# Ordinary Phoenix lifecycle collector correction

The collector now creates identity-lifecycle/ under its output and supplies
MIXER_KEY_OWNER_LIFECYCLE_EVIDENCE to the existing ordinary test run. Existing
artifact upload retains that directory, including failed KOL09 observations.
The production fixture-exclusion command now includes the supervisor export and
requires fixture init rejection with exact probe owner/workers/admission absent
before and after. The direct init callback probe starts no child.

Only hosted/scripts/test-local.py changed. Nine canonical methods, adverse
assertions, Supervisor, fixture, dependency pins and workflow are unchanged. The
source diff and production command prefix are frozen for independent review.
Python AST/hash/diff checks passed; no collector or Elixir code ran locally.

Root must separately deliver/select the remote run and inspect actual method
results, production exclusion and nine expected lifecycle JSON files. The
currently running earlier CI cannot validate this unpushed correction. Full
remote suite scope differs from the local custody contract and cannot qualify
that protocol. The failed local custody execution remains held and preserved;
this packet performs no retry, process probe or replacement controller work.
