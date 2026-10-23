# Apple baseline review

Root inspected all eight original screenshots through the image viewer and
reran the producer's integrity verifier against the frozen Git source. The
captures are accepted as the unchanged iOS27 simulator reference for the four
shared documents in light/dark, including Arabic RTL/accessibility text. They are
not a shared renderer or physical parity result.

The large navigation title, prominent section headings, rounded grouped list
surfaces, green active switch and role-based button labels provide the concrete
iOS design reference. The current sharedCandidate1 descriptor is a data fixture
and provisional recipe; its caption-sized section heading, title-based navigation,
accent-colored switch and simpler list geometry are not accepted as an exact
match to this reference. Final native styling must preserve the shared iOS design
on Android; applying a different native Android default is not a solution.

The foundation codec/math and pure resolver can be implemented and reviewed
independently of that token refinement. Before qualifying renderer parity, add
explicit shared recipes/metrics for the observed navigation/section/switch/group
appearance, measure native geometry and fonts, and compare both rendered outputs.
Do not silently change sealed candidate data or label these screenshots as a
qualification of a theme that they do not consume. No Apple font redistribution
or exact raster/glyph identity is required or inferred by this data reference.

No physical devices, native input/accessibility interaction, installed signed
capture, release, dogfood or GA gate passes. Root's visual review is an engineering
reference decision, not a claim that the user reviewed or approved final tokens.
