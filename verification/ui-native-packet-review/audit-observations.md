The first audit checker assumed artifact values were bare hashes. The producer schema instead records {sha256,bytes}; the corrected checker verifies both properties. This was a checker schema error; no producer bytes changed.
SDK output reports separate MixerUI39/MixerCore10/MixerApple2 runs; the checker now sums their51 tests rather than expecting one total line.
